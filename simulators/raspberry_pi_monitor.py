#!/usr/bin/env python3
"""
Raspberry Pi Advanced System Monitor
Complete IoT device with GPIO control and system monitoring
Install: sudo pip3 install paho-mqtt psutil RPi.GPIO gpiozero
"""

import json
import time
import socket
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
import psutil

# Try to import GPIO libraries (Raspberry Pi specific)
try:
    import RPi.GPIO as GPIO
    from gpiozero import LED, Button, MCP3008
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️ GPIO libraries not available - running without GPIO support")
    GPIO_AVAILABLE = False

class RaspberryPiMonitor:
    def __init__(self, device_id="raspberrypi_01", mqtt_broker="192.168.1.247", mqtt_port=1883):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # Device info
        self.device_type = "raspberry_pi_monitor"
        self.location = "Server kambarys"
        self.firmware_version = "3.0.0"
        
        # GPIO Setup (if available)
        self.gpio_setup()
        
        # MQTT client setup
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Monitoring settings
        self.cpu_alert_threshold = 80.0    # %
        self.temp_alert_threshold = 70.0   # °C
        self.memory_alert_threshold = 85.0 # %
        self.disk_alert_threshold = 90.0   # %
        
        # State tracking
        self.last_alerts = {}
        self.relay_states = {"relay1": False, "relay2": False}
        
    def gpio_setup(self):
        """Setup GPIO pins if available"""
        if not GPIO_AVAILABLE:
            return
            
        try:
            # Setup GPIO pins
            self.status_led = LED(18)      # Status LED
            self.relay1 = LED(23)          # Relay 1 (Apšvietimas)
            self.relay2 = LED(24)          # Relay 2 (Ventiliatorius)
            self.button = Button(21)       # Control button
            
            # ADC for analog sensors (optional)
            try:
                self.adc = MCP3008(channel=0)  # Analog sensor input
            except:
                self.adc = None
                
            # Button callback
            self.button.when_pressed = self.button_pressed
            
            print("✅ GPIO initialized successfully")
            self.status_led.blink(0.5, 0.5)  # Blink status LED
            
        except Exception as e:
            print(f"❌ GPIO setup failed: {e}")
            
    def button_pressed(self):
        """Handle button press"""
        self.send_alert("Mygtukas paspaustas", "INFO")
        if GPIO_AVAILABLE:
            self.status_led.on()
            time.sleep(0.5)
            self.status_led.off()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT: {self.mqtt_broker}")
            
            # Subscribe to control topic
            control_topic = f"iot/devices/{self.device_id}/control"
            client.subscribe(control_topic)
            print(f"📡 Subscribed to: {control_topic}")
            
            # Send initial status
            self.send_device_status()
            
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            command = msg.payload.decode()
            print(f"📨 Command received: {command}")
            
            # Basic commands
            if command == "status":
                self.send_device_status()
            elif command == "restart":
                self.send_alert("Raspberry Pi perkraunamas", "INFO")
                time.sleep(2)
                subprocess.run(["sudo", "reboot"])
            elif command == "shutdown":
                self.send_alert("Raspberry Pi išjungiamas", "WARNING")
                time.sleep(2)
                subprocess.run(["sudo", "shutdown", "-h", "now"])
            elif command == "get_data":
                self.send_all_sensor_data()
                
            # GPIO Control commands
            elif command == "relay1_on" and GPIO_AVAILABLE:
                self.control_relay("relay1", True)
            elif command == "relay1_off" and GPIO_AVAILABLE:
                self.control_relay("relay1", False)
            elif command == "relay2_on" and GPIO_AVAILABLE:
                self.control_relay("relay2", True)
            elif command == "relay2_off" and GPIO_AVAILABLE:
                self.control_relay("relay2", False)
            elif command == "led_blink" and GPIO_AVAILABLE:
                self.status_led.blink(0.2, 0.2, n=5)
                
            # System commands
            elif command == "update_system":
                self.update_system()
            elif command == "check_services":
                self.check_services()
            elif command == "get_logs":
                self.send_system_logs()
                
        except Exception as e:
            print(f"❌ Error processing command: {e}")
    
    def control_relay(self, relay_name, state):
        """Control GPIO relays"""
        if not GPIO_AVAILABLE:
            return
            
        try:
            if relay_name == "relay1":
                if state:
                    self.relay1.on()
                else:
                    self.relay1.off()
            elif relay_name == "relay2":
                if state:
                    self.relay2.on()
                else:
                    self.relay2.off()
                    
            self.relay_states[relay_name] = state
            status_text = "ĮJUNGTAS" if state else "IŠJUNGTAS"
            device_name = "Apšvietimas" if relay_name == "relay1" else "Ventiliatorius"
            
            self.send_alert(f"{device_name} {status_text}", "INFO")
            self.send_device_status()
            
        except Exception as e:
            self.send_alert(f"Relay control error: {e}", "ERROR")
    
    def get_cpu_temperature(self):
        """Get CPU temperature"""
        try:
            # Raspberry Pi CPU temperature
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
        except:
            # Alternative method
            try:
                result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                     capture_output=True, text=True)
                temp_str = result.stdout.strip()
                temp = float(temp_str.split('=')[1].split("'")[0])
                return round(temp, 1)
            except:
                return None
    
    def get_system_info(self):
        """Get comprehensive system information"""
        info = {}
        
        # CPU Information
        info['cpu_percent'] = psutil.cpu_percent(interval=1)
        info['cpu_count'] = psutil.cpu_count()
        info['cpu_freq'] = psutil.cpu_freq().current if psutil.cpu_freq() else None
        info['cpu_temp'] = self.get_cpu_temperature()
        
        # Memory Information
        memory = psutil.virtual_memory()
        info['memory_total'] = round(memory.total / 1024**3, 2)  # GB
        info['memory_used'] = round(memory.used / 1024**3, 2)    # GB
        info['memory_percent'] = memory.percent
        
        # Disk Information
        disk = psutil.disk_usage('/')
        info['disk_total'] = round(disk.total / 1024**3, 2)      # GB
        info['disk_used'] = round(disk.used / 1024**3, 2)        # GB
        info['disk_percent'] = round((disk.used / disk.total) * 100, 1)
        
        # Network Information
        net_io = psutil.net_io_counters()
        info['network_sent'] = round(net_io.bytes_sent / 1024**2, 2)     # MB
        info['network_recv'] = round(net_io.bytes_recv / 1024**2, 2)     # MB
        
        # System uptime
        boot_time = psutil.boot_time()
        info['uptime_hours'] = round((time.time() - boot_time) / 3600, 1)
        
        # Load average
        try:
            load_avg = psutil.getloadavg()
            info['load_1min'] = round(load_avg[0], 2)
            info['load_5min'] = round(load_avg[1], 2)
            info['load_15min'] = round(load_avg[2], 2)
        except:
            info['load_1min'] = None
            
        return info
    
    def send_device_status(self):
        """Send comprehensive device status"""
        topic = f"iot/devices/{self.device_id}/status"
        
        system_info = self.get_system_info()
        
        status_data = {
            "device_id": self.device_id,
            "online": True,
            "type": self.device_type,
            "location": self.location,
            "firmware_version": self.firmware_version,
            "timestamp": datetime.now().isoformat(),
            "ip_address": self.get_local_ip(),
            "hostname": socket.gethostname(),
            "system_info": system_info,
            "gpio_available": GPIO_AVAILABLE,
            "relay_states": self.relay_states
        }
        
        payload = json.dumps(status_data, indent=2)
        self.client.publish(topic, payload)
        print(f"📤 Status sent - CPU: {system_info['cpu_percent']}%, Temp: {system_info['cpu_temp']}°C")
    
    def send_all_sensor_data(self):
        """Send all sensor readings"""
        topic = f"iot/devices/{self.device_id}/data"
        timestamp = datetime.now().isoformat()
        
        system_info = self.get_system_info()
        
        # Send individual sensor readings
        sensors = [
            ("cpu_usage", system_info['cpu_percent'], "%"),
            ("cpu_temperature", system_info['cpu_temp'], "°C"),
            ("memory_usage", system_info['memory_percent'], "%"),
            ("disk_usage", system_info['disk_percent'], "%"),
            ("uptime", system_info['uptime_hours'], "hours"),
            ("load_1min", system_info['load_1min'], "")
        ]
        
        for sensor_type, value, unit in sensors:
            if value is not None:
                sensor_data = {
                    "device_id": self.device_id,
                    "sensor_type": sensor_type,
                    "value": value,
                    "unit": unit,
                    "timestamp": timestamp
                }
                self.client.publish(topic, json.dumps(sensor_data))
        
        # Read analog sensor if available
        if GPIO_AVAILABLE and self.adc:
            try:
                analog_value = self.adc.value * 100  # Convert to percentage
                analog_data = {
                    "device_id": self.device_id,
                    "sensor_type": "analog_input",
                    "value": round(analog_value, 1),
                    "unit": "%",
                    "timestamp": timestamp
                }
                self.client.publish(topic, json.dumps(analog_data))
            except Exception as e:
                print(f"❌ Analog read error: {e}")
        
        # Check for alerts
        self.check_system_alerts(system_info)
    
    def check_system_alerts(self, system_info):
        """Check for system alerts and send if necessary"""
        current_time = time.time()
        
        # CPU Usage Alert
        if system_info['cpu_percent'] > self.cpu_alert_threshold:
            if 'cpu_high' not in self.last_alerts or current_time - self.last_alerts['cpu_high'] > 300:  # 5 min
                self.send_alert(f"Aukšta CPU apkrova: {system_info['cpu_percent']}%", "WARNING")
                self.last_alerts['cpu_high'] = current_time
        
        # Temperature Alert
        if system_info['cpu_temp'] and system_info['cpu_temp'] > self.temp_alert_threshold:
            if 'temp_high' not in self.last_alerts or current_time - self.last_alerts['temp_high'] > 300:
                self.send_alert(f"Aukšta CPU temperatūra: {system_info['cpu_temp']}°C", "CRITICAL")
                self.last_alerts['temp_high'] = current_time
        
        # Memory Alert
        if system_info['memory_percent'] > self.memory_alert_threshold:
            if 'memory_high' not in self.last_alerts or current_time - self.last_alerts['memory_high'] > 600:  # 10 min
                self.send_alert(f"Aukšta RAM naudojimo: {system_info['memory_percent']}%", "WARNING")
                self.last_alerts['memory_high'] = current_time
        
        # Disk Alert
        if system_info['disk_percent'] > self.disk_alert_threshold:
            if 'disk_high' not in self.last_alerts or current_time - self.last_alerts['disk_high'] > 3600:  # 1 hour
                self.send_alert(f"Mažai disko vietos: {system_info['disk_percent']}% užimta", "CRITICAL")
                self.last_alerts['disk_high'] = current_time
    
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
            "source": "raspberry_pi"
        }
        
        self.client.publish("iot/alerts", json.dumps(alert_data))
        print(f"🚨 Alert: {message}")
    
    def check_services(self):
        """Check important system services"""
        services = ["ssh", "mosquitto", "nginx", "docker"]
        
        for service in services:
            try:
                result = subprocess.run(['systemctl', 'is-active', service], 
                                     capture_output=True, text=True)
                status = result.stdout.strip()
                
                if status != "active":
                    self.send_alert(f"Servisas {service} neveikia", "WARNING")
                    
            except Exception as e:
                print(f"Service check error: {e}")
    
    def update_system(self):
        """Update system packages (careful!)"""
        self.send_alert("Pradedamas sistemos atnaujinimas", "INFO")
        
        try:
            # Update package list
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            self.send_alert("Paketų sąrašas atnaujintas", "INFO")
            
            # Upgrade packages (non-interactive)
            result = subprocess.run(['sudo', 'apt', 'list', '--upgradable'], 
                                 capture_output=True, text=True)
            
            upgradable_count = len(result.stdout.split('\n')) - 2
            
            if upgradable_count > 0:
                self.send_alert(f"Rasta {upgradable_count} atnaujinimų", "INFO")
            else:
                self.send_alert("Sistema atnaujinta", "INFO")
                
        except Exception as e:
            self.send_alert(f"Atnaujinimo klaida: {e}", "ERROR")
    
    def send_system_logs(self):
        """Send recent system logs"""
        try:
            # Get last 10 lines from syslog
            result = subprocess.run(['sudo', 'tail', '-10', '/var/log/syslog'], 
                                 capture_output=True, text=True)
            
            log_lines = result.stdout.split('\n')[:5]  # First 5 lines
            log_summary = ' | '.join(log_lines)
            
            self.send_alert(f"Sistemos log: {log_summary}", "INFO")
            
        except Exception as e:
            self.send_alert(f"Log skaitymo klaida: {e}", "ERROR")
    
    def run(self):
        """Main monitoring loop"""
        try:
            print(f"🔄 Connecting to MQTT: {self.mqtt_broker}:{self.mqtt_port}")
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            
            # Start MQTT loop
            self.client.loop_start()
            
            print(f"🚀 Raspberry Pi Monitor started: {self.device_id}")
            
            # Main monitoring loop
            while True:
                self.send_all_sensor_data()
                time.sleep(30)  # Send data every 30 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down monitor...")
            if GPIO_AVAILABLE:
                self.status_led.off()
                GPIO.cleanup()
            self.client.loop_stop()
            self.client.disconnect()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.send_alert(f"Monitor error: {e}", "ERROR")

if __name__ == "__main__":
    # Configuration
    DEVICE_ID = "raspberrypi_main"
    MQTT_BROKER = "192.168.1.247"  # Replace with your IP
    
    # Create and start monitor
    monitor = RaspberryPiMonitor(DEVICE_ID, MQTT_BROKER)
    monitor.run()
