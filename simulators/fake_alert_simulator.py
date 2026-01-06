#!/usr/bin/env python3
"""
Fake PC Alert Simulator
Sends critical alerts every minute to test push notifications
"""

import json
import time
import ssl
import random
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class FakeAlertSimulator:
    def __init__(self):
        self.device_id = f"fake_pc_test"
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 8883))
        self.mqtt_username = os.getenv('MQTT_USERNAME')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')
        self.use_tls = os.getenv('MQTT_USE_TLS', 'true').lower() == 'true'
        
        # MQTT setup
        self.client = mqtt.Client(client_id=f"fake_alert_{random.randint(1000,9999)}")
        self.client.on_connect = self.on_connect
        
        if self.mqtt_username and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        if self.use_tls:
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        
        # Alert scenarios
        self.alert_scenarios = [
            {"level": "CRITICAL", "message": "CPU temperatūra per aukšta: 95°C", "type": "temperature"},
            {"level": "CRITICAL", "message": "GPU temperatūra kritinė: 98°C", "type": "temperature"},
            {"level": "WARNING", "message": "RAM užimtumas aukštas: 92%", "type": "memory"},
            {"level": "CRITICAL", "message": "Diskas beveik pilnas: 98% užimta", "type": "disk"},
            {"level": "WARNING", "message": "CPU apkrova labai didelė: 99%", "type": "cpu"},
            {"level": "ERROR", "message": "Tinklo ryšys nutrūko", "type": "network"},
            {"level": "CRITICAL", "message": "Sistemos ventiliatorius sustojo!", "type": "fan"},
            {"level": "WARNING", "message": "Baterijos lygis žemas: 5%", "type": "battery"},
        ]
        
        self.alert_index = 0
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Prisijungta prie MQTT brokerio")
        else:
            print(f"❌ Nepavyko prisijungti: {rc}")
    
    def connect(self):
        print(f"🔄 Jungiamasi prie {self.mqtt_broker}:{self.mqtt_port}...")
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ Klaida: {e}")
            return False
    
    def send_alert(self):
        """Send a random critical alert"""
        scenario = self.alert_scenarios[self.alert_index]
        self.alert_index = (self.alert_index + 1) % len(self.alert_scenarios)
        
        alert_data = {
            "level": scenario["level"],
            "message": scenario["message"],
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "source": "fake_simulator",
            "type": scenario["type"]
        }
        
        topic = "iot/alerts"
        payload = json.dumps(alert_data)
        
        result = self.client.publish(topic, payload)
        if result.rc == 0:
            emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "ERROR": "❌"}.get(scenario["level"], "📢")
            print(f"{emoji} [{scenario['level']}] {scenario['message']}")
        else:
            print(f"❌ Nepavyko išsiųsti alerto")
    
    def send_device_status(self):
        """Send fake device status"""
        status = {
            "device_id": self.device_id,
            "online": True,
            "type": "fake_test_device",
            "location": "Test Environment",
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"iot/devices/{self.device_id}/status"
        self.client.publish(topic, json.dumps(status))
    
    def run(self, interval_seconds=60):
        """Run simulator - send alert every interval"""
        if not self.connect():
            return
        
        print(f"\n🎭 Fake Alert Simulator")
        print(f"========================")
        print(f"Device ID: {self.device_id}")
        print(f"Intervalas: kas {interval_seconds} sekundžių")
        print(f"Alertų tipai: {len(self.alert_scenarios)}")
        print(f"\n⏰ Siunčiu alertus... (Ctrl+C sustabdyti)\n")
        
        # Send initial status
        self.send_device_status()
        
        try:
            while True:
                self.send_alert()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n🛑 Simuliatorius sustabdytas")
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    import sys
    
    # Check for custom interval
    interval = 60  # default 1 minute
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except:
            pass
    
    simulator = FakeAlertSimulator()
    simulator.run(interval_seconds=interval)
