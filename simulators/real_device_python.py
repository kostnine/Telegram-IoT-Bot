#!/usr/bin/env python3
"""
Real IoT Device Example - Python (Raspberry Pi)
Requires: pip install paho-mqtt psutil
"""

import json
import time
import socket
from datetime import datetime
import paho.mqtt.client as mqtt
import psutil  # For system monitoring

class RealIoTDevice:
    def __init__(self, device_id, mqtt_broker, mqtt_port=1883):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # MQTT client setup
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Device info
        self.device_type = "system_monitor"
        self.location = "Server Room"
        self.firmware_version = "1.0.0"
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker: {self.mqtt_broker}")
            
            # Subscribe to control topic
            control_topic = f"iot/devices/{self.device_id}/control"
            client.subscribe(control_topic)
            print(f"📡 Subscribed to: {control_topic}")
            
            # Send initial status
            self.send_device_status()
        else:
            print(f"❌ Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            command = msg.payload.decode()
            print(f"📨 Received command: {command}")
            
            if command == "status":
                self.send_device_status()
            elif command == "restart":
                print("🔄 Restart command received")
                # Add restart logic here
            elif command == "get_data":
                self.send_sensor_data()
                
        except Exception as e:
            print(f"❌ Error processing command: {e}")
    
    def send_device_status(self):
        """Send device status to MQTT"""
        topic = f"iot/devices/{self.device_id}/status"
        
        status_data = {
            "device_id": self.device_id,
            "online": True,
            "type": self.device_type,
            "location": self.location,
            "firmware_version": self.firmware_version,
            "timestamp": datetime.now().isoformat(),
            "ip_address": self.get_local_ip()
        }
        
        payload = json.dumps(status_data)
        self.client.publish(topic, payload)
        print(f"📤 Status sent: {status_data}")
    
    def send_sensor_data(self):
        """Send real sensor data (system metrics)"""
        topic = f"iot/devices/{self.device_id}/data"
        timestamp = datetime.now().isoformat()
        
        # CPU Temperature (Raspberry Pi)
        try:
            cpu_temp = self.get_cpu_temperature()
            if cpu_temp:
                temp_data = {
                    "device_id": self.device_id,
                    "sensor_type": "temperature",
                    "value": cpu_temp,
                    "unit": "°C",
                    "timestamp": timestamp
                }
                self.client.publish(topic, json.dumps(temp_data))
        except:
            pass
        
        # CPU Usage
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_data = {
            "device_id": self.device_id,
            "sensor_type": "cpu_usage",
            "value": cpu_usage,
            "unit": "%",
            "timestamp": timestamp
        }
        self.client.publish(topic, json.dumps(cpu_data))
        
        # Memory Usage
        memory = psutil.virtual_memory()
        memory_data = {
            "device_id": self.device_id,
            "sensor_type": "memory_usage",
            "value": memory.percent,
            "unit": "%",
            "timestamp": timestamp
        }
        self.client.publish(topic, json.dumps(memory_data))
        
        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_data = {
            "device_id": self.device_id,
            "sensor_type": "disk_usage",
            "value": (disk.used / disk.total) * 100,
            "unit": "%",
            "timestamp": timestamp
        }
        self.client.publish(topic, json.dumps(disk_data))
        
        print(f"📊 Sensor data sent: CPU={cpu_usage}%, Memory={memory.percent}%")
        
        # Send alert if CPU usage too high
        if cpu_usage > 80:
            self.send_alert(f"High CPU usage: {cpu_usage}%", "WARNING")
    
    def get_cpu_temperature(self):
        """Get CPU temperature (Raspberry Pi)"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
        except:
            return None
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "unknown"
    
    def send_alert(self, message, level="INFO"):
        """Send alert to MQTT"""
        alert_data = {
            "device_id": self.device_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "device"
        }
        
        self.client.publish("iot/alerts", json.dumps(alert_data))
        print(f"🚨 Alert sent: {message}")
    
    def connect_and_run(self):
        """Connect to MQTT and start monitoring"""
        try:
            print(f"🔄 Connecting to MQTT broker: {self.mqtt_broker}:{self.mqtt_port}")
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            
            # Start MQTT loop in background
            self.client.loop_start()
            
            print(f"🚀 Device {self.device_id} started")
            
            # Main monitoring loop
            while True:
                self.send_sensor_data()
                time.sleep(30)  # Send data every 30 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping device...")
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Configuration
    DEVICE_ID = "raspberry_pi_01"
    MQTT_BROKER = "192.168.1.100"  # Replace with your computer's IP
    
    # Create and start device
    device = RealIoTDevice(DEVICE_ID, MQTT_BROKER)
    device.connect_and_run()
