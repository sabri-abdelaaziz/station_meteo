import paho.mqtt.client as mqtt
import psycopg2
import json
import boto3
import sys

# ========================================================
# Paramètres du projet
# ========================================================
AWS_REGION = "eu-west-1"
# Assurez-vous que ceci est le nom exact du secret
SECRET_NAME = "rds!db-a06cefb4-3c92-47bd-8107-16c2a79d2ade"
RDS_HOST = "weather-db.cbyaqii4u8ul.eu-west-1.rds.amazonaws.com"
RDS_USER = "weather_user"
RDS_DB_NAME = "weather"

# Paramètres MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "esp8266/captures/data"

# ========================================================
# Fonction pour récupérer le mot de passe depuis AWS (optimisée)
# ========================================================
def get_password_from_aws():
    print(f"Tentative de récupération du secret : {SECRET_NAME}...")
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    
    try:
        resp = client.get_secret_value(SecretId=SECRET_NAME)
        if 'SecretString' in resp:
            secret_data = resp['SecretString']
            try:
                secret_json = json.loads(secret_data)
                # Recherche intelligente d'un mot-clé standard du mot de passe
                possible_keys = ['password', f'{RDS_USER}_password', 'rds_password']
                for key in possible_keys:
                    if key in secret_json:
                        print(f" Mot de passe trouvé avec la clé : '{key}'")
                        return secret_json[key]
                
                # Si aucune clé standard n'a été trouvée
                print(f"Impossible de trouver une clé standard. Clés disponibles : {list(secret_json.keys())}")
                return None

            except json.JSONDecodeError:
                print(" Le secret n'est pas au format JSON, utilisation en texte brut.")
                return secret_data
    except Exception as e:
        print(f" [Erreur AWS Security] : {e}")
        return None
    return None

# ========================================================
# Fonction d'envoi des métriques à CloudWatch
# ========================================================
def send_metric_to_cloudwatch(temp):
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)
        cloudwatch.put_metric_data(
            Namespace='IoT_Project_Metrics',
            MetricData=[{'MetricName': 'Temperature', 'Unit': 'Count', 'Value': float(temp)}]
        )
        # print(" Métrique envoyée à CloudWatch.") # Activez pour vérifier
    except Exception as e:
        print(f" [Erreur AWS Monitor] : {e}")

# ========================================================
# Initialisation de la connexion à la base de données
# ========================================================
print(" Initialisation du pont (Bridge)...")
RDS_PASSWORD = get_password_from_aws()

if not RDS_PASSWORD:
    print("\n ERREUR CRITIQUE : Impossible de récupérer le mot de passe de la base. Arrêt du programme.")
    sys.exit(1)
else:
    print(" Mot de passe récupéré avec succès.")

# ========================================================
# Fonctions MQTT et logique principale
# ========================================================
def save_to_rds(dev_id, temp, hum, rain_val, soil_moist, light_lvl, air_qual):
    conn = None
    try:
        # Paramètres de connexion (inchangés)
        conn = psycopg2.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB_NAME,
            connect_timeout=10
        )
        cur = conn.cursor()

        # Requête SQL correspondant exactement à la nouvelle structure
        sql = """
            INSERT INTO sensor_readings
            (device_id, temperature, humidity, rain, soil_moisture, light_level, air_quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        # Exécution avec les paramètres dans l'ordre correct
        cur.execute(sql, (dev_id, temp, hum, rain_val, soil_moist, light_lvl, air_qual))
        
        conn.commit()
        cur.close()

        # Message de confirmation avec toutes les données
        print(f"[Enregistré] Dev:{dev_id} | T:{temp} | H:{hum} | Rain:{rain_val} | Soil:{soil_moist} | Light:{light_lvl} | Air:{air_qual}")

        # Envoi vers CloudWatch (optionnel – seulement la température)
        if temp is not None:
            send_metric_to_cloudwatch(temp)

    except psycopg2.OperationalError as e:
        print(f"[Erreur connexion DB]: {e}")
    except Exception as e:
        print(f"[Erreur DB] : {e}")
    finally:
        if conn:
            conn.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(" Connecté au broker MQTT local !")
        client.subscribe(MQTT_TOPIC)
        print(f" Abonné au topic : {MQTT_TOPIC}")
        print(" Le pont est PRÊT et en attente de données...")
    else:
        print(f" Echec de connexion au broker MQTT, code retour : {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"\n Message reçu : {payload}")
        data = json.loads(payload)
        
        dev_id = data.get('device_id', 'ESP32_Default')
        # Extraction des données avec valeurs par défaut
        t = data.get('temperature')
        h = data.get('humidity')
        r = data.get('rain')
        s = data.get('soil_moisture')
        l = data.get('light_level')
        a = data.get('air_quality')

        # Vérification des données reçues
        if t is not None and h is not None and a is not None:
            save_to_rds(dev_id, t, h, r, s, l, a)
        else:
            print("Données incomplètes reçues, enregistrement ignoré.")

    except json.JSONDecodeError:
        print(f" [Erreur Data] : Format JSON invalide.")
    except Exception as e:
        print(f" [Erreur Processing] : {e}")

# Démarrage
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f" Connexion au broker MQTT sur {MQTT_BROKER}:{MQTT_PORT}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except ConnectionRefusedError:
    print(f"\n ERREUR CRITIQUE : Impossible de se connecter à Mosquitto sur {MQTT_BROKER}:{MQTT_PORT}.")
    print(" Vérifiez que Mosquitto fonctionne et que 'listener 1883' est bien configuré.")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n Pont arrêté par l'utilisateur.")