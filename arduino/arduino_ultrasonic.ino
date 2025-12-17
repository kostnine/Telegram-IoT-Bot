/*
Arduino + HC-SR04 Ultrasonic Distance Sensor
For NodeMCU ESP8266 with WiFi capability
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// 📡 WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// 🔧 MQTT Configuration
const char* mqtt_server = "192.168.1.247";
const int mqtt_port = 1883;
const char* device_id = "ultrasonic_01";

// 📏 Ultrasonic HC-SR04 Configuration
#define TRIGGER_PIN D1  // GPIO5
#define ECHO_PIN D2     // GPIO4
#define LED_PIN D4      // Built-in LED (GPIO2)
#define BUZZER_PIN D3   // Optional buzzer

WiFiClient espClient;
PubSubClient client(espClient);

// 📊 Sensor settings
float distance_cm = 0;
float max_distance = 400; // Maximum reliable distance
float min_alert_distance = 10; // Alert if object closer than 10cm
float max_alert_distance = 300; // Alert if distance > 300cm (sensor failure)
unsigned long last_measurement = 0;
unsigned long last_status = 0;

void setup() {
  Serial.begin(115200);
  
  // 🔧 Initialize pins
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  digitalWrite(LED_PIN, HIGH); // LED off (inverted on NodeMCU)
  digitalWrite(BUZZER_PIN, LOW);
  
  // 📡 Connect to WiFi
  connectToWiFi();
  
  // 🔧 Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
  
  connectToMQTT();
  
  Serial.println("🚀 Ultrasonic Distance Sensor Ready!");
  blinkLED(3);
}

void loop() {
  if (!client.connected()) {
    connectToMQTT();
  }
  client.loop();
  
  // 📏 Measure distance every 2 seconds
  if (millis() - last_measurement > 2000) {
    measureAndSendDistance();
    last_measurement = millis();
  }
  
  // 📤 Send status every 30 seconds
  if (millis() - last_status > 30000) {
    sendDeviceStatus();
    last_status = millis();
  }
  
  delay(50);
}

void connectToWiFi() {
  Serial.print("📡 Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n✅ WiFi connected!");
  Serial.print("📍 IP: ");
  Serial.println(WiFi.localIP());
}

void connectToMQTT() {
  while (!client.connected()) {
    Serial.print("🔄 Connecting to MQTT...");
    
    if (client.connect(device_id)) {
      Serial.println(" connected!");
      
      String controlTopic = "iot/devices/" + String(device_id) + "/control";
      client.subscribe(controlTopic.c_str());
      
      sendDeviceStatus();
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

void measureAndSendDistance() {
  // 📏 Trigger pulse
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  
  // 📏 Read echo
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  
  if (duration == 0) {
    Serial.println("❌ Ultrasonic timeout!");
    sendAlert("Ultrasonic sensor timeout", "ERROR");
    return;
  }
  
  // 📊 Calculate distance (speed of sound = 343 m/s)
  distance_cm = (duration * 0.034) / 2;
  
  // 🔍 Validate measurement
  if (distance_cm > max_distance) {
    Serial.println("❌ Distance out of range");
    return;
  }
  
  // 📤 Send distance data
  String topic = "iot/devices/" + String(device_id) + "/data";
  String timestamp = String(millis());
  
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["sensor_type"] = "distance";
  doc["value"] = round(distance_cm * 10) / 10.0; // Round to 1 decimal
  doc["unit"] = "cm";
  doc["timestamp"] = timestamp;
  doc["signal_quality"] = calculateSignalQuality(duration);
  
  String payload;
  serializeJson(doc, payload);
  client.publish(topic.c_str(), payload.c_str());
  
  Serial.printf("📏 Distance: %.1f cm\n", distance_cm);
  
  // 🚨 Check alerts
  checkDistanceAlerts(distance_cm);
}

int calculateSignalQuality(unsigned long duration) {
  // Signal quality based on echo duration (rough estimate)
  if (duration < 1000) return 100;        // Excellent
  else if (duration < 5000) return 80;    // Good  
  else if (duration < 10000) return 60;   // Fair
  else if (duration < 20000) return 40;   // Poor
  else return 20;                         // Very poor
}

void checkDistanceAlerts(float distance) {
  if (distance < min_alert_distance) {
    sendAlert("OBJEKTAS ARTI: " + String(distance) + "cm!", "WARNING");
    soundBuzzer(3); // 3 short beeps
    blinkLED(5);
  } 
  else if (distance > max_alert_distance) {
    sendAlert("Sensorius galimai sugedo: " + String(distance) + "cm", "ERROR");
  }
  else if (distance < 50) {
    // Object detected within 50cm
    sendAlert("Objektas aptiktas " + String(distance) + "cm atstumu", "INFO");
    soundBuzzer(1); // 1 beep
  }
}

void sendDeviceStatus() {
  String topic = "iot/devices/" + String(device_id) + "/status";
  
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["online"] = true;
  doc["type"] = "ultrasonic_distance_sensor";
  doc["location"] = "Įėjimo durys";
  doc["firmware_version"] = "1.5.0";
  doc["timestamp"] = String(millis());
  doc["ip_address"] = WiFi.localIP().toString();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["last_distance"] = distance_cm;
  doc["max_range"] = max_distance;
  doc["uptime_ms"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish(topic.c_str(), payload.c_str());
  Serial.println("📤 Status sent");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println("📨 Command: " + message);
  
  if (message == "status") {
    sendDeviceStatus();
  }
  else if (message == "measure") {
    measureAndSendDistance();
  }
  else if (message == "calibrate") {
    calibrateSensor();
  }
  else if (message == "beep") {
    soundBuzzer(2);
  }
  else if (message == "restart") {
    sendAlert("Ultrasonic sensor perkraunamas", "INFO");
    delay(1000);
    ESP.restart();
  }
  else if (message.startsWith("set_min_alert:")) {
    float new_min = message.substring(14).toFloat();
    if (new_min > 0 && new_min < 100) {
      min_alert_distance = new_min;
      sendAlert("Min alert distance: " + String(new_min) + "cm", "INFO");
    }
  }
}

void calibrateSensor() {
  sendAlert("Kalibruojama... Palaukite 10 sekundžių", "INFO");
  
  float total = 0;
  int valid_readings = 0;
  
  for (int i = 0; i < 20; i++) {
    digitalWrite(TRIGGER_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_PIN, LOW);
    
    unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);
    if (duration > 0) {
      float dist = (duration * 0.034) / 2;
      if (dist < max_distance) {
        total += dist;
        valid_readings++;
      }
    }
    delay(500);
  }
  
  if (valid_readings > 5) {
    float avg_distance = total / valid_readings;
    sendAlert("Kalibravimas baigtas. Vid. atstumas: " + String(avg_distance) + "cm", "INFO");
  } else {
    sendAlert("Kalibravimas nepavyko - per mažai duomenų", "ERROR");
  }
}

void soundBuzzer(int beeps) {
  for (int i = 0; i < beeps; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
  }
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, LOW);  // LED on (inverted)
    delay(150);
    digitalWrite(LED_PIN, HIGH); // LED off
    delay(150);
  }
}

void sendAlert(String message, String level) {
  JsonDocument doc;
  doc["device_id"] = device_id;
  doc["level"] = level;
  doc["message"] = message;
  doc["timestamp"] = String(millis());
  doc["source"] = "ultrasonic_device";
  doc["distance_cm"] = distance_cm;
  
  String payload;
  serializeJson(doc, payload);
  
  client.publish("iot/alerts", payload.c_str());
  Serial.println("🚨 Alert: " + message);
}
