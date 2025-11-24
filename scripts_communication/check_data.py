import psycopg2
import json
import boto3

# ==========================================
# Paramètres du projet
# ==========================================
AWS_REGION = "eu-west-1"
SECRET_NAME = "rds!db-a06cefb4-3c92-47bd-8107-16c2a79d2ade"
RDS_HOST = "weather-db.cbyaqii4u8ul.eu-west-1.rds.amazonaws.com"
RDS_USER = "weather_user"
RDS_DB_NAME = "weather"

# ========================================================
# Fonction de récupération du mot de passe
# ========================================================
def get_password_from_aws():
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    try:
        resp = client.get_secret_value(SecretId=SECRET_NAME)
        if 'SecretString' in resp:
            secret_data = resp['SecretString']
            try:
                secret_json = json.loads(secret_data)
                possible_keys = ['password', f'{RDS_USER}_password', 'rds_password']
                for key in possible_keys:
                    if key in secret_json:
                        return secret_json[key]
                return list(secret_json.values())[0]
            except json.JSONDecodeError:
                return secret_data
    except Exception as e:
        print(f" Error getting secret: {e}")
    return None

# ========================================================
# Fonction d'affichage des données (8 colonnes uniquement)
# ========================================================
def show_data():
    print(" Connexion à la base de données AWS RDS...")
    password = get_password_from_aws()
    
    if not password:
        print(" Échec de la récupération du mot de passe.")
        return

    try:
        conn = psycopg2.connect(
            host=RDS_HOST, user=RDS_USER, password=password, database=RDS_DB_NAME
        )
        cur = conn.cursor()

        # 1. La requête demande uniquement 8 colonnes (sans timestamp)
        query = """
            SELECT id, device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality 
            FROM sensor_readings 
            ORDER BY id DESC 
            LIMIT 10;
        """
        
        cur.execute(query)
        rows = cur.fetchall()

        if not rows:
            print("\n Aucune donnée disponible dans la table pour le moment.")
            cur.close()
            conn.close()
            return

        # 2. Formatage du tableau pour seulement 8 colonnes
        print("\n" + "="*95)
        print(f" {'AWS RDS MONITOR (Données en direct)':^90} ")
        print("="*95)
        
        header = f"{'ID':<5} | {'Device':<14} | {'Temp':<6} | {'Hum':<6} | {'Rain':<6} | {'Soil':<6} | {'Light':<6} | {'Air Q':<6}"
        print(header)
        print("-" * 95)

        for row in rows:
            # 3. Décomposition en 8 variables uniquement (correction du problème d'unpacking)
            r_id, dev, temp, hum, rain, soil, light, air = row
            
            # Gestion des valeurs nulles
            dev = str(dev) if dev else "Unknown"
            temp = f"{temp:.1f}" if temp is not None else "--"
            hum = f"{hum:.1f}" if hum is not None else "--"
            
            print(f"{r_id:<5} | {dev:<14} | {temp:<6} | {hum:<6} | {str(rain):<6} | {str(soil):<6} | {str(light):<6} | {str(air):<6}")

        print("="*95 + "\n")
        
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f" Database Error: {e}")
    except Exception as e:
        print(f" General Error: {e}")

if __name__ == "__main__":
    show_data()
