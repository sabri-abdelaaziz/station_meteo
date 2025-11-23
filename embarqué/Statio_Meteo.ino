#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <BearSSLHelpers.h>
#include <time.h> 

// ----------------------------------------
// WIFI + MQTT TLS CONFIG
// ----------------------------------------
const char* ssid = "ORANGE-DIGITAL-CENTER";//configurer  SSID
const char* password = "Welcome@2023";
const char* mqtt_server = "108.129.254.33";
const uint16_t mqtt_port = 8883;

// ----------------------------------------
// ONLY CA CERTIFICATE (SERVER VERIFICATION)
// ----------------------------------------
const char ca_cert[] PROGMEM =
"-----BEGIN CERTIFICATE-----\n"
"MIIDizCCAnOgAwIBAgIUZy2EC+OBfj7f5oxeviu+YI8EEZYwDQYJKoZIhvcNAQEL\n"
"BQAwVTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM\n"
"GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDEOMAwGA1UEAwwFbXktQ0EwHhcNMjUx\n"
"MDI3MjMzNDU3WhcNMjgwODE2MjMzNDU3WjBVMQswCQYDVQQGEwJBVTETMBEGA1UE\n"
"CAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRk\n"
"MQ4wDAYDVQQDDAVteS1DQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB\n"
"AMgd7dVOBnatyntp+wuyO2DszQLQkt+9GRss/VpjGcNUjerU9GU0V0I47704sCPH\n"
"ku3R4AiE7MrTjNP7b9puB0Q+fjJu2iGtEZhfsG2H+jeXSoqp2mqdriE1/JhcaMao\n"
"f4pxic/XeOo64z8KjkQ9+ja2r6JrGyCg6HBeQGm/jmgpj1S/GgF0lhEJhfj6h5NA\n"
"sEdG/sMCTGtrVJoeo7C7X/K1hHCyFtAjo0ZQ1WQVtVtE3LWa508fTJwNvMa5S69z\n"
"2N5yv+xYBhiTi0IgJbnAx92KJpbnBVrMakx1Q6lOxg8zVJcntTJp19Mc5Tn/YOC5\n"
"w4T7lcXU8uwmBFwnXyGrPocCAwEAAaNTMFEwHQYDVR0OBBYEFI+BVILt8Sxsjwvh\n"
"WwHqCZBmmoTZMB8GA1UdIwQYMBaAFI+BVILt8SxsjwvhWwHqCZBmmoTZMA8GA1Ud\n"
"EwEB/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAJ+IF09v/uXWd5WfJMBvcTqg\n"
"yRIxdEgxKVXgy/7Icy3fgRdyPtasgwqzfCZX/M/Yg8+AvTajylaG8SiFXfz0wKUo\n"
"SfqbFYrPYGpa7NCxk4ZZ87cLhBo2QVQA2T/bYmj6962q4oAW3VNregSJX3cXEiRI\n"
"lT5lC7bY3AZdtO7pA32RUyC6sNVb/xa4fQHNW7c5jg8wOIL/MstUM+rMeQVzFNBK\n"
"v1EvQiKoM8sU/GWFEQaB/mGKPm36nfsf3BZ43g4Eo/AyfaW5ZM2Z49U+oAzroEj0\n"
"ixHdLDd8R2T522RghXsTBkeS2Az2BA4CA0Ihr/zF+37hfhlENyIaxXMPe13P/vk=\n"
"-----END CERTIFICATE-----\n";

// ----------------------------------------
// SSL OBJECTS
// ----------------------------------------
BearSSL::X509List cert(ca_cert);
WiFiClientSecure espClient;
PubSubClient client(espClient);

// ----------------------------------------
// Matériel
// ----------------------------------------
#define DHTPIN D5
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define MUX_C1 D1
#define MUX_C2 D2
#define MUX_C3 D3
#define MUX_C4 D4

// ----------------------------------------
// Topics
// ----------------------------------------
const char* topic_data = "esp8266/captures/data";
const char* topic_status = "esp8266/station/status";

unsigned long lastSend = 0;

void setup_wifi();
void reconnect();
void selectMultiplexeur(int canal);

// ----------------------------------------
void setup() {
  Serial.begin(115200);
  delay(10);

  dht.begin();
  delay(2000);

  pinMode(MUX_C1, OUTPUT);
  pinMode(MUX_C2, OUTPUT);
  pinMode(MUX_C3, OUTPUT);
  pinMode(MUX_C4, OUTPUT);

  setup_wifi(); 

  // Only CA certificate → server authentication only
  espClient.setTrustAnchors(&cert);

  client.setServer(mqtt_server, mqtt_port);
}

// ----------------------------------------
void setup_wifi() {
  Serial.println();
  Serial.print("Connexion à : ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - start > 20000) {
      Serial.println("\nEchec connexion WiFi (timeout). Redémarrage...");
      ESP.restart();
    }
  }

  Serial.println("\nWiFi connecté !");
  Serial.print("IP : ");
  Serial.println(WiFi.localIP());

  Serial.println("\nSynchronisation NTP...");
  configTime(3600, 0, "pool.ntp.org");

  time_t now = time(nullptr);
  while (now < 1672531199) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println(" OK !");
}

// ----------------------------------------
void reconnect() {
  if (!WiFi.isConnected()) setup_wifi();

  while (!client.connected()) {
    Serial.print("Connexion MQTT TLS... ");

    if (client.connect("ESP8266_Client_TLS")) {
      Serial.println("OK !");
      client.publish(topic_status, "online");
    } else {
      Serial.print("Erreur (rc=");
      Serial.print(client.state());
      char buf[256];
      espClient.getLastSSLError(buf, 256);
      Serial.print(" SSL Error: ");
      Serial.print(buf);
      Serial.println("). Retry in 5s...");
      delay(5000);
    }
  }
}

// ----------------------------------------
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  unsigned long now = millis();
  if (now - lastSend < 10000) return;
  lastSend = now;

  selectMultiplexeur(1); delay(20);
  int val_rain = analogRead(A0);
   
  selectMultiplexeur(2); delay(20);
  int val_soil = analogRead(A0);
   
  selectMultiplexeur(3); delay(20);
  int val_ldr = analogRead(A0);
   
  selectMultiplexeur(4); delay(20);
  int val_mq135 = analogRead(A0);

  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t)) {
    Serial.println("Erreur lecture DHT22 !");
    client.publish(topic_status, "dht_error");
    return;
  }

  String payload = "{";
  payload += "\"temperature\":" + String(t, 1) + ",";
  payload += "\"humidity\":" + String(h, 1) + ",";
  payload += "\"rain\":" + String(val_rain) + ",";
  payload += "\"soil_moisture\":" + String(val_soil) + ",";
  payload += "\"light_level\":" + String(val_ldr) + ",";
  payload += "\"air_quality\":" + String(val_mq135);
  payload += "}";

  Serial.print("Envoi : ");
  Serial.println(payload);

  client.publish(topic_data, payload.c_str());
}

// ----------------------------------------
void selectMultiplexeur(int canal) {
  digitalWrite(MUX_C1, LOW);
  digitalWrite(MUX_C2, LOW);
  digitalWrite(MUX_C3, LOW);
  digitalWrite(MUX_C4, LOW);

  switch(canal) {
    case 1: digitalWrite(MUX_C1, HIGH); break;
    case 2: digitalWrite(MUX_C2, HIGH); break;
    case 3: digitalWrite(MUX_C3, HIGH); break;
    case 4: digitalWrite(MUX_C4, HIGH); break;
  }
}