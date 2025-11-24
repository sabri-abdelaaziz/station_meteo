import psycopg2
import json
import boto3
import sys

# ========================================================
# Paramètres de connexion
# ========================================================
AWS_REGION = "eu-west-1"
SECRET_NAME = "rds!db-a06cefb4-3c92-47bd-8107-16c2a79d2ade"
RDS_HOST = "weather-db.cbyaqii4u8ul.eu-west-1.rds.amazonaws.com"
RDS_USER = "weather_user"
RDS_DB_NAME = "weather"

# --- Fonction pour récupérer le mot de passe ---
def get_password():
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    try:
        resp = client.get_secret_value(SecretId=SECRET_NAME)
        if 'SecretString' in resp:
            secret = json.loads(resp['SecretString'])
            for key in secret:
                if 'password' in key:
                    return secret[key]
    except Exception as e:
        print(f"Erreur lors de la récupération du secret : {e}")
    return None

def reset_table():
    print("Connexion à la base de données...")
    password = get_password()
    if not password:
        print("Impossible d'obtenir le mot de passe.")
        return

    conn = None
    try:
        conn = psycopg2.connect(
            host=RDS_HOST, user=RDS_USER, password=password, database=RDS_DB_NAME
        )
        conn.autocommit = True  # Important pour exécuter les commandes DDL telles que DROP/CREATE
        cur = conn.cursor()

        print("\nAttention : l'ancienne table et toutes ses données seront supprimées maintenant.")

        # Suppression de l'ancienne table si elle existe
        cur.execute("DROP TABLE IF EXISTS sensor_readings;")
        print("Ancienne table 'sensor_readings' supprimée avec succès.")

        # Création de la nouvelle table
        print("Création de la nouvelle table...")
        create_query = """
        CREATE TABLE sensor_readings (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            device_id VARCHAR(50),
            temperature FLOAT,
            humidity FLOAT,
            rain INTEGER,
            soil_moisture FLOAT,
            light_level FLOAT,
            air_quality FLOAT
        );
        """
        cur.execute(create_query)
        print("Nouvelle table 'sensor_readings' créée avec succès.")

        cur.close()
    except Exception as e:
        print(f"Erreur pendant l'opération : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Demande de confirmation à l'utilisateur
    confirm = input("Êtes-vous sûr de vouloir supprimer l'ancienne table et en créer une nouvelle ? (tapez 'yes' pour continuer) : ")
    if confirm.lower() == 'yes':
        reset_table()
    else:
        print("Opération annulée.")