#!/usr/bin/env python3
"""
Free Virtual IoT Devices - No Hardware Required!
Simulate multiple IoT devices with realistic behavior
"""

import json
import time
import random
import threading
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

class VirtualIoTDevice:
    def __init__(self, device_id, device_type, location, mqtt_broker="localhost"):
        self.device_id = device_id
        self.device_type = device_type
        self.location = location
        self.mqtt_broker = mqtt_broker
        
        # MQTT client
        self.client = mqtt.Client(client_id=f"virtual_{device_id}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Device state
        self.online = True
        self.running = True
        
        # Sensor simulation parameters
        self.base_values = self._get_base_values()
        self.sensor_drift = 0.0  # Gradual sensor drift over time
        
    def _get_base_values(self):
        """Get realistic base values for different device types"""
        if "temperature" in self.device_type:
            return {"temperature": 22.0, "humidity": 45.0}
        elif "pressure" in self.device_type:
            return {"pressure": 1013.25, "temperature": 20.0}
        elif "smart_home" in self.device_type:
            return {"temperature": 21.0, "humidity": 40.0, "light": 300, "motion": False}
        elif "industrial" in self.device_type:
            return {"vibration": 2.5, "temperature": 45.0, "pressure": 150.0}
        else:
            return {"value": 50.0}
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ {self.device_id} connected to MQTT")
            
            # Subscribe to control topic
            control_topic = f"iot/devices/{self.device_id}/control"
            client.subscribe(control_topic)
            
            # Send initial status
            self.send_device_status()
        else:
            print(f"❌ {self.device_id} connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            command = msg.payload.decode()
            print(f"📨 {self.device_id} received: {command}")
            
            if command == "status":
                self.send_device_status()
            elif command == "restart":
                self.simulate_restart()
            elif command == "calibrate":
                self.simulate_calibration()
            elif command == "test_alert":
                self.send_test_alert()
            elif command.startswith("set_"):
                self.handle_setting_change(command)
                
        except Exception as e:
            print(f"❌ Command error: {e}")
    
    def send_device_status(self):
        """Send realistic device status"""
        topic = f"iot/devices/{self.device_id}/status"
        
        status_data = {
            "device_id": self.device_id,
            "online": self.online,
            "type": self.device_type,
            "location": self.location,
            "firmware_version": f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
            "timestamp": datetime.now().isoformat(),
            "battery_level": random.randint(20, 100) if "sensor" in self.device_type else None,
            "signal_strength": random.randint(-80, -30),
            "uptime_seconds": random.randint(3600, 864000)  # 1 hour to 10 days
        }
        
        self.client.publish(topic, json.dumps(status_data))
        print(f"📤 {self.device_id} status sent")
    
    def generate_sensor_data(self):
        """Generate realistic sensor data with trends and anomalies"""
        timestamp = datetime.now().isoformat()
        
        for sensor_type, base_value in self.base_values.items():
            # Simulate realistic variations
            if sensor_type == "temperature":
                # Daily temperature cycle + random variation + gradual drift
                hour = datetime.now().hour
                daily_cycle = 3 * math.sin((hour - 6) * math.pi / 12)
                random_variation = random.uniform(-2, 2)
                value = base_value + daily_cycle + random_variation + self.sensor_drift
                unit = "°C"
                
                # Occasional temperature spikes (simulate heating/cooling events)
                if random.random() < 0.05:  # 5% chance
                    value += random.uniform(5, 15)
                    
            elif sensor_type == "humidity":
                # Humidity inversely related to temperature changes
                temp_effect = -0.5 * (self.base_values.get("temperature", 22) - 22)
                random_variation = random.uniform(-5, 5)
                value = max(0, min(100, base_value + temp_effect + random_variation))
                unit = "%"
                
            elif sensor_type == "pressure":
                # Atmospheric pressure with weather simulation
                weather_trend = random.uniform(-2, 2)  # Simulate weather changes
                value = base_value + weather_trend + random.uniform(-0.5, 0.5)
                unit = "hPa"
                
            elif sensor_type == "light":
                # Light level based on time of day
                hour = datetime.now().hour
                if 6 <= hour <= 18:  # Daytime
                    value = random.randint(200, 1000)
                else:  # Nighttime
                    value = random.randint(0, 50)
                unit = "lux"
                
            elif sensor_type == "vibration":
                # Industrial vibration with occasional spikes
                base_vibration = random.uniform(1.0, 3.0)
                if random.random() < 0.1:  # 10% chance of vibration spike
                    value = random.uniform(8.0, 15.0)
                else:
                    value = base_vibration
                unit = "mm/s"
                
            elif sensor_type == "motion":
                # Motion detection (boolean)
                value = random.random() < 0.15  # 15% chance of motion
                unit = ""
                
            else:
                value = base_value + random.uniform(-10, 10)
                unit = ""
            
            # Send sensor data
            sensor_data = {
                "device_id": self.device_id,
                "sensor_type": sensor_type,
                "value": round(value, 2) if isinstance(value, float) else value,
                "unit": unit,
                "timestamp": timestamp,
                "quality": random.randint(85, 100)  # Signal quality
            }
            
            topic = f"iot/devices/{self.device_id}/data"
            self.client.publish(topic, json.dumps(sensor_data))
            
            # Check for alerts
            self.check_sensor_alerts(sensor_type, value)
    
    def check_sensor_alerts(self, sensor_type, value):
        """Generate realistic alerts based on sensor values"""
        alert_conditions = {
            "temperature": [
                (lambda v: v > 35, "CRITICAL", f"Kritiškai aukšta temperatūra: {value:.1f}°C"),
                (lambda v: v > 30, "WARNING", f"Aukšta temperatūra: {value:.1f}°C"), 
                (lambda v: v < 5, "WARNING", f"Žema temperatūra: {value:.1f}°C")
            ],
            "humidity": [
                (lambda v: v > 85, "WARNING", f"Aukšta drėgmė: {value:.1f}%"),
                (lambda v: v < 15, "WARNING", f"Žema drėgmė: {value:.1f}%")
            ],
            "pressure": [
                (lambda v: v < 1000, "WARNING", f"Žemas spaudimas: {value:.1f} hPa"),
                (lambda v: v > 1025, "INFO", f"Aukštas spaudimas: {value:.1f} hPa")
            ],
            "vibration": [
                (lambda v: v > 10, "CRITICAL", f"Pavojinga vibracija: {value:.1f} mm/s"),
                (lambda v: v > 5, "WARNING", f"Padidėjusi vibracija: {value:.1f} mm/s")
            ]
        }
        
        conditions = alert_conditions.get(sensor_type, [])
        for condition, level, message in conditions:
            if condition(value):
                self.send_alert(message, level)
                break  # Only send one alert per sensor reading
    
    def send_alert(self, message, level="WARNING"):
        """Send alert to MQTT"""
        alert_data = {
            "device_id": self.device_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": f"virtual_{self.device_type}",
            "location": self.location
        }
        
        self.client.publish("iot/alerts", json.dumps(alert_data))
        print(f"🚨 {self.device_id} alert: {message}")
    
    def simulate_restart(self):
        """Simulate device restart"""
        self.send_alert(f"{self.device_id} perkraunamas", "INFO")
        time.sleep(2)
        self.send_alert(f"{self.device_id} paleistas sėkmingai", "INFO")
        self.send_device_status()
    
    def simulate_calibration(self):
        """Simulate sensor calibration"""
        self.send_alert(f"{self.device_id} kalibruojamas...", "INFO")
        time.sleep(5)
        # Reset sensor drift
        self.sensor_drift = 0
        self.send_alert(f"{self.device_id} kalibravimas baigtas", "INFO")
    
    def send_test_alert(self):
        """Send test alert"""
        test_messages = [
            "Testavimo pranešimas",
            "Sensoriaus testas sėkmingas", 
            "Sistemos patikrinimas OK",
            "Duomenų perdavimas veikia"
        ]
        message = random.choice(test_messages)
        self.send_alert(message, "INFO")
    
    def handle_setting_change(self, command):
        """Handle device setting changes"""
        try:
            _, setting, value = command.split(":")
            self.send_alert(f"Nustatymas keičiamas: {setting} = {value}", "INFO")
        except:
            self.send_alert("Nežinomas nustatymas", "ERROR")
    
    def run_device_simulation(self, interval=15):
        """Main device simulation loop"""
        try:
            print(f"🚀 Starting {self.device_id} simulation")
            self.client.connect(self.mqtt_broker, 1883, 60)
            self.client.loop_start()
            
            while self.running:
                if self.online:
                    # Send sensor data
                    self.generate_sensor_data()
                    
                    # Occasional status updates
                    if random.random() < 0.1:  # 10% chance
                        self.send_device_status()
                    
                    # Simulate sensor drift over time
                    self.sensor_drift += random.uniform(-0.01, 0.01)
                    self.sensor_drift = max(-2, min(2, self.sensor_drift))  # Limit drift
                    
                    # Simulate occasional connectivity issues
                    if random.random() < 0.02:  # 2% chance
                        print(f"⚠️ {self.device_id} simulating connectivity issue")
                        self.online = False
                        time.sleep(random.randint(5, 30))  # Offline for 5-30 seconds
                        self.online = True
                        self.send_alert(f"{self.device_id} atjungtas tinklui", "INFO")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"🛑 Stopping {self.device_id}")
        except Exception as e:
            print(f"❌ {self.device_id} error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

# Import math for sine calculations
import math

def create_virtual_iot_ecosystem():
    """Create a complete virtual IoT ecosystem"""
    
    devices = [
        # Smart Home Devices
        VirtualIoTDevice("smart_thermostat", "smart_home_temperature", "Svetainė"),
        VirtualIoTDevice("bedroom_sensor", "temperature_humidity_sensor", "Miegamasis"),
        VirtualIoTDevice("kitchen_sensor", "smart_home_multisensor", "Virtuvė"),
        VirtualIoTDevice("garage_door", "smart_home_security", "Garažas"),
        
        # Industrial Devices  
        VirtualIoTDevice("pump_station_01", "industrial_monitor", "Siurblių stotis"),
        VirtualIoTDevice("conveyor_belt", "industrial_vibration", "Gamybos linija"),
        VirtualIoTDevice("pressure_tank", "pressure_monitor", "Kompresoriaus kambaris"),
        
        # Environmental Sensors
        VirtualIoTDevice("weather_station", "environmental_sensor", "Stogo terasa"),
        VirtualIoTDevice("air_quality", "environmental_air", "Miesto centras"),
        VirtualIoTDevice("soil_moisture", "agricultural_sensor", "Šiltnamis Nr.1")
    ]
    
    print("🌐 Launching Virtual IoT Ecosystem!")
    print("📱 Check your Telegram bot - you should see 10 new devices!")
    
    # Start all devices in separate threads
    threads = []
    for device in devices:
        thread = threading.Thread(
            target=device.run_device_simulation,
            args=(random.randint(10, 20),),  # Random intervals 10-20 seconds
            daemon=True
        )
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Stagger device startup
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(60)
            print(f"📊 Virtual IoT Ecosystem running... {len(devices)} devices active")
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Virtual IoT Ecosystem...")
        for device in devices:
            device.running = False

if __name__ == "__main__":
    create_virtual_iot_ecosystem()
