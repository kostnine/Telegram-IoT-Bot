/*
ESP32 + DHT22 Complete IoT Device
Compatible with Telegram IoT Bot
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

// 📡 WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 🔧 MQTT Configuration  
const char* mqtt_server = "192.168.1.247";  // Jūsų kompiuterio IP
const int mqtt_port = 1883;
const char* device_id = "esp32_temp_01";

// 🌡️ DHT22 Configuration
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define LED_PIN 2           // Built-in LED
#define RELAY_PIN 5         // Relay control (optional)

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient espClient;
PubSubClient client(espClient);

// ⏰ NTP Time
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 7200); // UTC+2 (Lietuva)

// 📊 Device State
bool relay_state = false;
unsigned long last_sensor_read = 0;
unsigned long last_status_send = 0;
float last_temperature = 0;
float last_humidity = 0;

void setup() {
  Serial.begin(115200);
  
  // 🔧 Initialize pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(RELAY_PIN, LOW);
  
  // 🌡️ Initialize DHT
  dht.begin();
  
  // 📡 Connect to WiFi
  connectToWiFi();
  
  // ⏰ Initialize time
  timeClient.begin();
  
  // 🔧 Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  client.setBufferSize(1024); // Increase buffer for JSON
  
  connectToMQTT();
  
  Serial.println("🚀 ESP32 IoT Device Ready!");
  blinkLED(3); // Success indicator
}

void loop() {
  // 🔧 Maintain connections
  if (!client.connected()) {
    connectToMQTT();
  }
  client.loop();
  
  // ⏰ Update time
  timeClient.update();
  
  // 📊 Send sensor data every 10 seconds
  if (millis() - last_sensor_read > 10000) {
    readAndSendSensorData();
    last_sensor_read = millis();
  }
  
  // 📤 Send status every 30 seconds
  if (millis() - last_status_send > 30000) {
    sendDeviceStatus();
    last_status_send = millis();
  }
  
  delay(100);
}

void connectToWiFi() {
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
    Serial.println("\n✅ WiFi connected!");
    Serial.print("📍 IP address: ");
    Serial.println(WiFi.localIP());
    blinkLED(2);
  } else {
    Serial.println("\n❌ WiFi connection failed!");
    ESP.restart(); // Restart if WiFi fails
  }
}

void connectToMQTT() {
  while (!client.connected()) {
    Serial.print("🔄 Connecting to MQTT...");
    
    if (client.connect(device_id)) {
      Serial.println(" connected!");
      
      // 📡 Subscribe to control topics
      String controlTopic = "iot/devices/" + String(device_id) + "/control";
      client.subscribe(controlTopic.c_str());
      Serial.println("📡 Subscribed to: " + controlTopic);
      
      sendDeviceStatus();
      blinkLED(1);
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

void sendDeviceStatus() {
  String topic = "iot/devices/" + String(device_id) + "/status";
  
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["online"] = true;
  doc["type"] = "temperature_humidity_sensor";
  doc["location"] = "Gyvenamasis kambarys";
  doc["firmware_version"] = "2.0.0";
  doc["timestamp"] = getCurrentTimestamp();
  doc["ip_address"] = WiFi.localIP().toString();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["relay_state"] = relay_state;
  doc["uptime_ms"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish(topic.c_str(), payload.c_str());
  Serial.println("📤 Status sent");
}

void readAndSendSensorData() {
  // 🌡️ Read DHT22
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("❌ DHT22 read failed!");
    sendAlert("DHT22 sensor reading failed", "ERROR");
    return;
  }
  
  last_temperature = temperature;
  last_humidity = humidity;
  
  String topic = "iot/devices/" + String(device_id) + "/data";
  String timestamp = getCurrentTimestamp();
  
  // 📤 Send temperature
  JsonDocument tempDoc;
  tempDoc["device_id"] = device_id;
  tempDoc["sensor_type"] = "temperature";
  tempDoc["value"] = round(temperature * 10) / 10.0; // Round to 1 decimal
  tempDoc["unit"] = "°C";
  tempDoc["timestamp"] = timestamp;
  
  String tempPayload;
  serializeJson(tempDoc, tempPayload);
  client.publish(topic.c_str(), tempPayload.c_str());
  
  // 📤 Send humidity
  JsonDocument humDoc;
  humDoc["device_id"] = device_id;
  humDoc["sensor_type"] = "humidity";
  humDoc["value"] = round(humidity * 10) / 10.0;
  humDoc["unit"] = "%";
  humDoc["timestamp"] = timestamp;
  
  String humPayload;
  serializeJson(humDoc, humPayload);
  client.publish(topic.c_str(), humPayload.c_str());
  
  Serial.printf("📊 T=%.1f°C, H=%.1f%%\n", temperature, humidity);
  
  // 🚨 Check for alerts
  checkTemperatureAlerts(temperature);
  checkHumidityAlerts(humidity);
}

void checkTemperatureAlerts(float temperature) {
  if (temperature > 30.0) {
    sendAlert("Aukšta temperatūra: " + String(temperature) + "°C", "WARNING");
  } else if (temperature < 10.0) {
    sendAlert("Žema temperatūra: " + String(temperature) + "°C", "WARNING");
  } else if (temperature > 35.0) {
    sendAlert("KRITIŠKAI aukšta temperatūra: " + String(temperature) + "°C", "CRITICAL");
  }
}

void checkHumidityAlerts(float humidity) {
  if (humidity > 80.0) {
    sendAlert("Aukšta drėgmė: " + String(humidity) + "%", "WARNING");
  } else if (humidity < 20.0) {
    sendAlert("Žema drėgmė: " + String(humidity) + "%", "WARNING");
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("📨 Command: " + message);
  
  // 🎮 Handle commands
  if (message == "status") {
    sendDeviceStatus();
  } 
  else if (message == "restart") {
    sendAlert("Įrenginys perkraunamas", "INFO");
    delay(1000);
    ESP.restart();
  }
  else if (message == "relay_on") {
    controlRelay(true);
  }
  else if (message == "relay_off") {
    controlRelay(false);
  }
  else if (message == "relay_toggle") {
    controlRelay(!relay_state);
  }
  else if (message == "led_blink") {
    blinkLED(5);
  }
  else if (message == "get_data") {
    readAndSendSensorData();
  }
  else {
    Serial.println("❓ Unknown command: " + message);
  }
}

void controlRelay(bool state) {
  relay_state = state;
  digitalWrite(RELAY_PIN, state ? HIGH : LOW);
  digitalWrite(LED_PIN, state ? HIGH : LOW); // LED follows relay
  
  String status = state ? "ĮJUNGTAS" : "IŠJUNGTAS";
  sendAlert("Relay " + status, "INFO");
  sendDeviceStatus(); // Update status immediately
  
  Serial.println("🔌 Relay: " + status);
}

void sendAlert(String message, String level) {
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["level"] = level;
  doc["message"] = message;
  doc["timestamp"] = getCurrentTimestamp();
  doc["source"] = "esp32_device";
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish("iot/alerts", payload.c_str());
  Serial.println("🚨 Alert: " + message);
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
}

String getCurrentTimestamp() {
  return timeClient.getFormattedTime() + " " + String(timeClient.getEpochTime());
}
