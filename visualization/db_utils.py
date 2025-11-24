from django.db import connection
from datetime import datetime
import logging
import os

# Setup file logger for aggregations (writes into app folder `logs/`)
_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, 'aggregations.log')
_AGG_LOGGER = logging.getLogger('visualization.aggregations')
if not _AGG_LOGGER.handlers:
    fh = logging.FileHandler(_LOG_FILE)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    _AGG_LOGGER.addHandler(fh)
    _AGG_LOGGER.setLevel(logging.INFO)


def ensure_tables():
    """Crée les tables PostgreSQL si elles n'existent pas.

    - `meteo_hourly(datetime TIMESTAMP PRIMARY KEY, temp_c FLOAT)`
    - `meteo_daily(date DATE PRIMARY KEY, temp_max FLOAT, temp_min FLOAT, temp_mean FLOAT)`
    - `meteo_10sec(datetime TIMESTAMP PRIMARY KEY, temp_c FLOAT)`
    """
    queries = [
        """
        CREATE TABLE IF NOT EXISTS meteo_hourly (
            datetime TIMESTAMP PRIMARY KEY,
            temp_c DOUBLE PRECISION
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS meteo_daily (
            date DATE PRIMARY KEY,
            temp_max DOUBLE PRECISION,
            temp_min DOUBLE PRECISION,
            temp_mean DOUBLE PRECISION
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS meteo_10sec (
            datetime TIMESTAMP PRIMARY KEY,
            temp_c DOUBLE PRECISION
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS aggregation_logs (
            id SERIAL PRIMARY KEY,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(32),
            details TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            device_id VARCHAR(50),
            temperature DOUBLE PRECISION,
            humidity DOUBLE PRECISION,
            rain INTEGER,
            soil_moisture DOUBLE PRECISION,
            light_level DOUBLE PRECISION,
            air_quality DOUBLE PRECISION
        );
        """,
    ]

    with connection.cursor() as cursor:
        for q in queries:
            cursor.execute(q)


def get_last_n(table_name: str, n: int = 10, column: str = 'temp_c'):
    """Retourne les dernières `n` valeurs d'une table donnée (ordre ascendente).

    Renvoie une liste de floats (peut être plus courte si peu de données).
    """
    # Sécuriser le nom de table/simple validation (éviter injections SQL via noms dynamiques)
    valid_tables = {'meteo_hourly', 'meteo_daily', 'meteo_10sec', 'sensor_readings', 'meteo'}
    if table_name not in valid_tables:
        raise ValueError(f"Table non autorisée: {table_name}")

    # Pour meteo_daily, le nom de la colonne par défaut peut être temp_mean
    if table_name == 'meteo_daily' and column == 'temp_c':
        column = 'temp_mean'

    query = f"SELECT {column} FROM {table_name} ORDER BY { 'date' if table_name=='meteo_daily' else 'datetime'} DESC LIMIT %s"

    with connection.cursor() as cursor:
        cursor.execute(query, [n])
        rows = cursor.fetchall()

    # rows est une liste de tuples
    values = [float(r[0]) for r in reversed(rows)] if rows else []
    return values


def aggregate_sensor_to_hourly():
    """Agrège les lectures de `sensor_readings` en moyennes horaires et insère/met à jour `meteo_hourly`.

    - Calcule AVG(temperature) par hour (date_trunc('hour', timestamp)).
    - N'insère que les heures nouvelles ou met à jour les heures existantes (upsert).
    - Idempotent : peut être exécuté plusieurs fois.
    """
    with connection.cursor() as cursor:
        # obtenir la dernière heure déjà agrégée (datetime stocké comme début d'heure)
        cursor.execute("SELECT MAX(datetime) FROM meteo_hourly")
        row = cursor.fetchone()
        last_dt = row[0] if row and row[0] is not None else None

        params = []
        where_clause = ""
        # Si on a déjà agrégé jusqu'à une heure, on recalculera depuis le début de cette heure
        # afin de prendre en compte d'éventuelles lectures tardives de la même heure.
        if last_dt:
            where_clause = "WHERE timestamp >= %s"
            # utiliser date_trunc('hour', last_dt) pour recalculer la dernière heure complète
            from_dt = last_dt.replace(minute=0, second=0, microsecond=0)
            params = [from_dt]

        agg_query = f"""
            SELECT date_trunc('hour', timestamp) AS hr, AVG(temperature) AS avg_temp
            FROM sensor_readings
            {where_clause}
            GROUP BY hr
            ORDER BY hr
        """

        cursor.execute(agg_query, params)
        rows = cursor.fetchall()

        for hr, avg_temp in rows:
            # upsert dans meteo_hourly
            cursor.execute(
                """
                INSERT INTO meteo_hourly (datetime, temp_c)
                VALUES (%s, %s)
                ON CONFLICT (datetime) DO UPDATE SET temp_c = EXCLUDED.temp_c
                """,
                [hr, float(avg_temp) if avg_temp is not None else None],
            )


def insert_sensor_reading(device_id: str = None, temperature: float = None, humidity: float = None,
                          rain: int = None, soil_moisture: float = None, light_level: float = None,
                          air_quality: float = None, timestamp=None):
    """Insère une lecture dans `sensor_readings`.

    - `timestamp` optionnel (si None, la valeur par défaut CURRENT_TIMESTAMP DB est utilisée).
    - Retourne l'id inséré.
    """
    with connection.cursor() as cursor:
        if timestamp is None:
            cursor.execute(
                """
                INSERT INTO sensor_readings (device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality],
            )
        else:
            cursor.execute(
                """
                INSERT INTO sensor_readings (timestamp, device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [timestamp, device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality],
            )
        row = cursor.fetchone()
        return row[0] if row else None


def aggregate_hourly_to_daily():
    """Agrège `meteo_hourly` en valeurs journalières (max/min/mean) dans `meteo_daily`.

    - Agrège les heures par date et upsert dans `meteo_daily`.
    - Idempotent.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(date) FROM meteo_daily")
        row = cursor.fetchone()
        last_date = row[0] if row and row[0] is not None else None

        params = []
        where_clause = ""
        if last_date:
            where_clause = "WHERE (datetime::date) > %s"
            params = [last_date]

        agg_query = f"""
            SELECT (datetime::date) AS d, MAX(temp_c) AS tmax, MIN(temp_c) AS tmin, AVG(temp_c) AS tmean
            FROM meteo_hourly
            {where_clause}
            GROUP BY d
            ORDER BY d
        """

        cursor.execute(agg_query, params)
        rows = cursor.fetchall()

        for d, tmax, tmin, tmean in rows:
            cursor.execute(
                """
                INSERT INTO meteo_daily (date, temp_max, temp_min, temp_mean)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE
                SET temp_max = EXCLUDED.temp_max,
                    temp_min = EXCLUDED.temp_min,
                    temp_mean = EXCLUDED.temp_mean
                """,
                [d, float(tmax) if tmax is not None else None, float(tmin) if tmin is not None else None, float(tmean) if tmean is not None else None],
            )


def run_aggregations():
    """Exécute les deux agrégations: sensor -> hourly puis hourly -> daily.

    Cette fonction écrit un log en base (`aggregation_logs`) et dans le fichier
    `visualization/logs/aggregations.log`. Retourne un tuple (status, details, log_id).
    """
    details = []
    status = 'success'
    log_id = None

    # Ensure tables exist (incl. aggregation_logs)
    try:
        ensure_tables()
    except Exception as e:
        _AGG_LOGGER.exception('ensure_tables failed')
        details.append(f'ensure_tables error: {e}')
        status = 'error'

    # Run sensor->hourly
    try:
        aggregate_sensor_to_hourly()
        details.append('aggregate_sensor_to_hourly: ok')
        _AGG_LOGGER.info('aggregate_sensor_to_hourly completed')
    except Exception as e:
        details.append(f'aggregate_sensor_to_hourly error: {e}')
        _AGG_LOGGER.exception('aggregate_sensor_to_hourly failed')
        status = 'error'

    # Run hourly->daily
    try:
        aggregate_hourly_to_daily()
        details.append('aggregate_hourly_to_daily: ok')
        _AGG_LOGGER.info('aggregate_hourly_to_daily completed')
    except Exception as e:
        details.append(f'aggregate_hourly_to_daily error: {e}')
        _AGG_LOGGER.exception('aggregate_hourly_to_daily failed')
        status = 'error'

    # Write DB log
    try:
        log_id = insert_aggregation_log(status, '\n'.join(details))
    except Exception as e:
        _AGG_LOGGER.exception('insert_aggregation_log failed')
        # If log insert fails, still return status/details

    return status, '\n'.join(details), log_id


def insert_aggregation_log(status: str, details: str):
    """Insère un enregistrement dans `aggregation_logs` et retourne l'id."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO aggregation_logs (status, details)
            VALUES (%s, %s)
            RETURNING id
            """,
            [status, details],
        )
        row = cursor.fetchone()
        return row[0] if row else None
