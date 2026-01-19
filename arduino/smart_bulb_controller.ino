/*
Smart Bulb Controller for Telegram IoT Bot
Controls RGB LED strip via MQTT commands
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Broker settings
const char* mqtt_server = "hfd4deff.ala.eu-central-1.emqxsl.com";
const int mqtt_port = 8883;
const char* mqtt_username = "Kostnine";
const char* mqtt_password = "Emilicrush228";
const char* device_id = "smart_bulb_01";

// LED pins (ESP32)
#define RED_PIN    25
#define GREEN_PIN  26
#define BLUE_PIN   27
#define POWER_PIN  32  // Relay or MOSFET control

WiFiClientSecure espClient;
PubSubClient client(espClient);

// Current bulb state
bool powerOn = false;
int currentRed = 255;
int currentGreen = 255;
int currentBlue = 255;

void setup() {
  Serial.begin(115200);
  
  // Initialize LED pins
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(POWER_PIN, OUTPUT);
  
  // Initial state - off
  digitalWrite(POWER_PIN, LOW);
  setLEDColor(0, 0, 0);
  
  // Connect to WiFi
  connectWiFi();
  
  // Configure MQTT SSL
  espClient.setInsecure(); // For testing - use proper certificates in production
  
  // Connect to MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  connectMQTT();
}

void loop() {
  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();
  
  // Send status every 30 seconds
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 30000) {
    sendStatus();
    lastStatus = millis();
  }
}

void connectWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    
    if (client.connect(device_id, mqtt_username, mqtt_password)) {
      Serial.println("connected!");
      
      // Subscribe to control topic
      char topic[50];
      sprintf(topic, "iot/devices/%s/control", device_id);
      client.subscribe(topic);
      
      // Send initial status
      sendStatus();
      
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  // Parse JSON command
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Process command
  if (doc.containsKey("action")) {
    String action = doc["action"];
    
    if (action == "power") {
      bool state = doc["state"];
      setPower(state);
    }
    else if (action == "color") {
      int r = doc["red"];
      int g = doc["green"];
      int b = doc["blue"];
      setColor(r, g, b);
    }
    else if (action == "brightness") {
      int brightness = doc["value"];
      setBrightness(brightness);
    }
    else if (action == "preset") {
      String preset = doc["name"];
      applyPreset(preset);
    }
    
    // Send updated status
    sendStatus();
  }
}

void setPower(bool state) {
  powerOn = state;
  digitalWrite(POWER_PIN, state ? HIGH : LOW);
  
  if (!state) {
    setLEDColor(0, 0, 0);  // Turn off LEDs when power is off
  } else {
    setLEDColor(currentRed, currentGreen, currentBlue);
  }
  
  Serial.printf("Power set to: %s\n", state ? "ON" : "OFF");
}

void setColor(int r, int g, int b) {
  currentRed = r;
  currentGreen = g;
  currentBlue = b;
  
  if (powerOn) {
    setLEDColor(r, g, b);
  }
  
  Serial.printf("Color set to: R=%d, G=%d, B=%d\n", r, g, b);
}

void setBrightness(int brightness) {
  // Scale current color by brightness (0-100)
  float factor = brightness / 100.0;
  int r = (int)(currentRed * factor);
  int g = (int)(currentGreen * factor);
  int b = (int)(currentBlue * factor);
  
  if (powerOn) {
    setLEDColor(r, g, b);
  }
  
  Serial.printf("Brightness set to: %d%%\n", brightness);
}

void setLEDColor(int r, int g, int b) {
  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

void applyPreset(String preset) {
  if (preset == "warm") {
    setColor(255, 200, 100);
  }
  else if (preset == "cool") {
    setColor(200, 200, 255);
  }
  else if (preset == "romantic") {
    setColor(255, 100, 150);
  }
  else if (preset == "party") {
    setColor(255, 0, 255);
  }
  else if (preset == "reading") {
    setColor(255, 255, 200);
  }
  
  Serial.printf("Applied preset: %s\n", preset.c_str());
}

void sendStatus() {
  StaticJsonDocument<200> doc;
  
  doc["device_id"] = device_id;
  doc["type"] = "smart_bulb";
  doc["online"] = true;
  doc["power"] = powerOn;
  doc["red"] = currentRed;
  doc["green"] = currentGreen;
  doc["blue"] = currentBlue;
  doc["timestamp"] = millis();
  
  char topic[50];
  sprintf(topic, "iot/devices/%s/status", device_id);
  
  String payload;
  serializeJson(doc, payload);
  client.publish(topic, payload.c_str());
  
  Serial.println("Status sent");
}
