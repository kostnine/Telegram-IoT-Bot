#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Broker
const char* mqtt_server = "192.168.1.100";  // Jūsų kompiuterio IP
const int mqtt_port = 1883;
const char* device_id = "real_sensor_01";

// Sensors
#define DHT_PIN 4
#define DHT_TYPE DHT22
DHT dht(DHT_PIN, DHT_TYPE);

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  dht.begin();
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected!");
  
  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  
  connectToMQTT();
  sendDeviceStatus();
}

void loop() {
  if (!client.connected()) {
    connectToMQTT();
  }
  client.loop();
  
  // Send sensor data every 10 seconds
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 10000) {
    sendSensorData();
    lastSend = millis();
  }
  
  delay(100);
}

void connectToMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect(device_id)) {
      Serial.println("connected");
      
      // Subscribe to control topic
      String controlTopic = "iot/devices/" + String(device_id) + "/control";
      client.subscribe(controlTopic.c_str());
      
      sendDeviceStatus();
    } else {
      Serial.print("failed, rc=");
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
  doc["location"] = "Living Room";
  doc["firmware_version"] = "1.0.0";
  doc["timestamp"] = getISOTimestamp();
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish(topic.c_str(), payload.c_str());
  Serial.println("Status sent: " + payload);
}

void sendSensorData() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read DHT sensor!");
    return;
  }
  
  String topic = "iot/devices/" + String(device_id) + "/data";
  String timestamp = getISOTimestamp();
  
  // Send temperature
  JsonDocument tempDoc;
  tempDoc["device_id"] = device_id;
  tempDoc["sensor_type"] = "temperature";
  tempDoc["value"] = temperature;
  tempDoc["unit"] = "°C";
  tempDoc["timestamp"] = timestamp;
  
  String tempPayload;
  serializeJson(tempDoc, tempPayload);
  client.publish(topic.c_str(), tempPayload.c_str());
  
  // Send humidity
  JsonDocument humDoc;
  humDoc["device_id"] = device_id;
  humDoc["sensor_type"] = "humidity";
  humDoc["value"] = humidity;
  humDoc["unit"] = "%";
  humDoc["timestamp"] = timestamp;
  
  String humPayload;
  serializeJson(humDoc, humPayload);
  client.publish(topic.c_str(), humPayload.c_str());
  
  Serial.printf("Sent: T=%.1f°C, H=%.1f%%\n", temperature, humidity);
  
  // Send alert if temperature too high
  if (temperature > 30.0) {
    sendAlert("Temperature exceeds 30°C!", "WARNING");
  }
}

void sendAlert(String message, String level) {
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["level"] = level;
  doc["message"] = message;
  doc["timestamp"] = getISOTimestamp();
  doc["source"] = "device";
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish("iot/alerts", payload.c_str());
  Serial.println("Alert sent: " + message);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("Received command: " + message);
  
  // Handle device control commands
  if (message == "status") {
    sendDeviceStatus();
  } else if (message == "restart") {
    ESP.restart();
  }
}

String getISOTimestamp() {
  // Simple timestamp - in real project use NTP
  return "2025-12-03T" + String(millis()/1000) + ".000Z";
}
