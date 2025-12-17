/*
ESP32 + DHT22 for EMQX Cloud
Compatible with Telegram IoT Bot
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ========== PAKEISK ŠIUOS NUSTATYMUS ==========

// 📡 WiFi - tavo namų WiFi
const char* ssid = "TAVO_WIFI_PAVADINIMAS";
const char* password = "TAVO_WIFI_SLAPTAZODIS";

// 🔧 MQTT - EMQX Cloud (iš tavo .env failo)
const char* mqtt_server = "hfd4deff.ala.eu-central-1.emqxsl.com";
const int mqtt_port = 8883;  // TLS portas
const char* mqtt_user = "Kostnine";
const char* mqtt_pass = "Emilicrush228";
const char* device_id = "esp32_sensor_01";  // Unikalus įrenginio ID

// ================================================

// 🌡️ DHT22 jutiklis
#define DHT_PIN 4        // GPIO4 - prijunk DHT22 DATA piną
#define DHT_TYPE DHT22
#define LED_PIN 2        // Įmontuotas LED

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClientSecure espClient;
PubSubClient client(espClient);

// Laikmačiai
unsigned long lastSensorRead = 0;
unsigned long lastStatusSend = 0;
const long sensorInterval = 10000;   // Skaityti kas 10 sek
const long statusInterval = 60000;   // Status kas 60 sek

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n🚀 ESP32 IoT Device Starting...");
  
  // LED setup
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // DHT setup
  dht.begin();
  
  // WiFi prisijungimas
  connectWiFi();
  
  // MQTT setup su TLS (be sertifikato tikrinimo - paprasčiau)
  espClient.setInsecure();  // Leidžia prisijungti be CA sertifikato
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(512);
  
  // Prisijungti prie MQTT
  connectMQTT();
  
  Serial.println("✅ ESP32 Ready!");
  blinkLED(3);
}

void loop() {
  // Palaikyti MQTT ryšį
  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();
  
  unsigned long now = millis();
  
  // Skaityti jutiklius kas 10 sek
  if (now - lastSensorRead >= sensorInterval) {
    lastSensorRead = now;
    readAndSendSensors();
  }
  
  // Siųsti status kas 60 sek
  if (now - lastStatusSend >= statusInterval) {
    lastStatusSend = now;
    sendDeviceStatus();
  }
}

void connectWiFi() {
  Serial.print("📡 Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi Failed! Restarting...");
    ESP.restart();
  }
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("🔧 Connecting to MQTT...");
    
    if (client.connect(device_id, mqtt_user, mqtt_pass)) {
      Serial.println(" ✅ Connected!");
      
      // Prenumeruoti valdymo komandas
      String controlTopic = "iot/devices/" + String(device_id) + "/control";
      client.subscribe(controlTopic.c_str());
      Serial.println("   Subscribed to: " + controlTopic);
      
      // Išsiųsti pradinį statusą
      sendDeviceStatus();
      
    } else {
      Serial.print(" ❌ Failed, rc=");
      Serial.println(client.state());
      Serial.println("   Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("📨 Command received: " + message);
  
  // Apdoroti komandas
  if (message == "led_on") {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("💡 LED ON");
  } 
  else if (message == "led_off") {
    digitalWrite(LED_PIN, LOW);
    Serial.println("💡 LED OFF");
  }
  else if (message == "status") {
    sendDeviceStatus();
  }
  else if (message == "restart") {
    Serial.println("🔄 Restarting...");
    ESP.restart();
  }
}

void readAndSendSensors() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  
  // Patikrinti ar skaitymas pavyko
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("❌ DHT read failed!");
    return;
  }
  
  Serial.printf("🌡️ Temp: %.1f°C  💧 Humidity: %.1f%%\n", temperature, humidity);
  
  // Siųsti temperatūrą
  sendSensorData("temperature", temperature, "°C");
  
  // Siųsti drėgmę
  sendSensorData("humidity", humidity, "%");
  
  // Blykstelėti LED
  blinkLED(1);
}

void sendSensorData(const char* sensorType, float value, const char* unit) {
  StaticJsonDocument<256> doc;
  doc["device_id"] = device_id;
  doc["sensor_type"] = sensorType;
  doc["value"] = value;
  doc["unit"] = unit;
  doc["timestamp"] = millis();
  
  char buffer[256];
  serializeJson(doc, buffer);
  
  String topic = "iot/devices/" + String(device_id) + "/data";
  client.publish(topic.c_str(), buffer);
}

void sendDeviceStatus() {
  StaticJsonDocument<512> doc;
  doc["device_id"] = device_id;
  doc["online"] = true;
  doc["type"] = "esp32_sensor";
  doc["location"] = "Home";  // Pakeisk į savo vietą
  doc["firmware_version"] = "1.0";
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["uptime_seconds"] = millis() / 1000;
  
  char buffer[512];
  serializeJson(doc, buffer);
  
  String topic = "iot/devices/" + String(device_id) + "/status";
  client.publish(topic.c_str(), buffer);
  
  Serial.println("📤 Status sent");
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}
