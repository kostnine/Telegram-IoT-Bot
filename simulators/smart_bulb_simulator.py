#!/usr/bin/env python3
"""
Smart Bulb Simulator for Telegram IoT Bot
Simulates RGB smart bulb with MQTT control
"""

import json
import time
import random
import logging
from datetime import datetime
from paho.mqtt.client import Client as MQTTClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartBulbSimulator:
    def __init__(self):
        # MQTT Configuration
        self.broker = os.getenv('MQTT_BROKER', 'hfd4deff.ala.eu-central-1.emqxsl.com')
        self.port = int(os.getenv('MQTT_PORT', 8883))
        self.username = os.getenv('MQTT_USERNAME', 'Kostnine')
        self.password = os.getenv('MQTT_PASSWORD', 'Emilicrush228')
        self.device_id = 'smart_bulb_01'
        
        # Bulb state
        self.power_on = False
        self.red = 255
        self.green = 255
        self.blue = 255
        self.brightness = 100
        
        # MQTT client
        self.client = MQTTClient(client_id=self.device_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Status topic
        self.status_topic = f"iot/devices/{self.device_id}/status"
        self.control_topic = f"iot/devices/{self.device_id}/control"
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            
            # Set credentials
            self.client.username_pw_set(self.username, self.password)
            
            # Enable TLS
            self.client.tls_set()
            
            # Connect
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            logger.info("Smart bulb simulator connected to MQTT")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """Called when client connects to broker"""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to control topic
            client.subscribe(self.control_topic)
            logger.info(f"Subscribed to: {self.control_topic}")
            
            # Send initial status
            self.send_status()
            
        else:
            logger.error(f"Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Called when message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"Message received on {topic}: {payload}")
            
            # Parse JSON command
            command = json.loads(payload)
            self.process_command(command)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """Called when client disconnects"""
        logger.warning("Disconnected from MQTT broker")
    
    def process_command(self, command):
        """Process received command"""
        try:
            action = command.get('action')
            
            if action == 'power':
                state = command.get('state', False)
                self.set_power(state)
                
            elif action == 'color':
                r = command.get('red', 255)
                g = command.get('green', 255)
                b = command.get('blue', 255)
                self.set_color(r, g, b)
                
            elif action == 'brightness':
                brightness = command.get('value', 100)
                self.set_brightness(brightness)
                
            elif action == 'preset':
                preset_name = command.get('name', '')
                self.apply_preset(preset_name)
                
            else:
                logger.warning(f"Unknown action: {action}")
            
            # Send updated status
            self.send_status()
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    def set_power(self, state):
        """Set bulb power state"""
        self.power_on = state
        logger.info(f"💡 Power set to: {'ON' if state else 'OFF'}")
        
        if not state:
            self.print_color("OFF", 0, 0, 0)
        else:
            self.print_color("ON", self.red, self.green, self.blue)
    
    def set_color(self, r, g, b):
        """Set bulb color"""
        self.red = max(0, min(255, r))
        self.green = max(0, min(255, g))
        self.blue = max(0, min(255, b))
        
        logger.info(f"🎨 Color set to RGB({self.red}, {self.green}, {self.blue})")
        
        if self.power_on:
            self.print_color("COLOR", self.red, self.green, self.blue)
    
    def set_brightness(self, brightness):
        """Set bulb brightness (0-100)"""
        self.brightness = max(0, min(100, brightness))
        logger.info(f"🔆 Brightness set to: {self.brightness}%")
        
        if self.power_on:
            # Apply brightness to current color
            factor = self.brightness / 100.0
            r = int(self.red * factor)
            g = int(self.green * factor)
            b = int(self.blue * factor)
            self.print_color("BRIGHTNESS", r, g, b)
    
    def apply_preset(self, preset_name):
        """Apply color preset"""
        presets = {
            "warm": (255, 200, 100),
            "cool": (200, 200, 255),
            "romantic": (255, 100, 150),
            "party": (255, 0, 255),
            "reading": (255, 255, 200),
            "sunset": (255, 150, 50),
            "ocean": (0, 150, 255),
            "forest": (50, 255, 50),
            "night": (255, 180, 80),    # Warm, low brightness
            "day": (255, 255, 255)      # Bright white
        }
        
        if preset_name in presets:
            r, g, b = presets[preset_name]
            self.set_color(r, g, b)
            logger.info(f"✨ Applied preset: {preset_name}")
        else:
            logger.warning(f"Unknown preset: {preset_name}")
    
    def send_status(self):
        """Send current status to MQTT"""
        try:
            status = {
                "device_id": self.device_id,
                "type": "smart_bulb",
                "online": True,
                "power": self.power_on,
                "red": self.red,
                "green": self.green,
                "blue": self.blue,
                "brightness": self.brightness,
                "timestamp": datetime.now().isoformat()
            }
            
            payload = json.dumps(status)
            self.client.publish(self.status_topic, payload)
            
            logger.info(f"📡 Status sent: Power={self.power_on}, RGB=({self.red},{self.green},{self.blue})")
            
        except Exception as e:
            logger.error(f"Error sending status: {e}")
    
    def print_color(self, action, r, g, b):
        """Print color representation to console"""
        # Simple text representation
        if r == 0 and g == 0 and b == 0:
            print(f"💡 {action}: ⚫ OFF")
        elif r == 255 and g == 255 and b == 255:
            print(f"💡 {action}: ⚪ WHITE")
        elif r > 200 and g < 100 and b < 100:
            print(f"💡 {action}: 🔴 RED")
        elif r < 100 and g > 200 and b < 100:
            print(f"💡 {action}: 🟢 GREEN")
        elif r < 100 and g < 100 and b > 200:
            print(f"💡 {action}: 🔵 BLUE")
        elif r > 200 and g > 200 and b < 100:
            print(f"💡 {action}: 🟡 YELLOW")
        elif r > 200 and g < 100 and b > 200:
            print(f"💡 {action}: 🟣 MAGENTA")
        elif r < 100 and g > 200 and b > 200:
            print(f"💡 {action}: 🔵 CYAN")
        else:
            print(f"💡 {action}: 🎨 RGB({r},{g},{b})")
    
    def run(self):
        """Run the simulator"""
        logger.info("🌟 Smart Bulb Simulator Starting...")
        logger.info(f"📱 Device ID: {self.device_id}")
        logger.info(f"🌐 MQTT Broker: {self.broker}")
        
        if not self.connect():
            logger.error("Failed to connect to MQTT broker")
            return
        
        try:
            logger.info("✅ Smart bulb simulator is running!")
            logger.info("💡 Waiting for commands from Telegram bot...")
            logger.info("🔄 Status updates every 30 seconds")
            
            # Send periodic status updates
            while True:
                time.sleep(30)
                self.send_status()
                
        except KeyboardInterrupt:
            logger.info("🛑 Smart bulb simulator stopped by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("📴 Disconnected from MQTT broker")

if __name__ == "__main__":
    simulator = SmartBulbSimulator()
    simulator.run()
