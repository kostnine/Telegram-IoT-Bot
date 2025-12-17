#!/usr/bin/env python3
"""
Simple IoT Device Simulator for Windows
Uses paho-mqtt with threading for better Windows compatibility
"""

import json
import random
import time
import threading
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleIoTDeviceSimulator:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = None
        self.connected = False
        self.running = False
        
        self.devices = {
            "temp_sensor_01": {
                "type": "temperature_sensor",
                "location": "Production Floor A",
                "min_temp": 18.0,
                "max_temp": 35.0
            },
            "humidity_sensor_01": {
                "type": "humidity_sensor", 
                "location": "Storage Room",
                "min_humidity": 30.0,
                "max_humidity": 80.0
            },
            "pump_01": {
                "type": "pump",
                "location": "Cooling System",
                "status": "running",
                "flow_rate": 150.0
            },
            "valve_01": {
                "type": "valve",
                "location": "Main Pipeline",
                "position": 75,
                "max_position": 100
            },
            "pressure_sensor_01": {
                "type": "pressure_sensor",
                "location": "Hydraulic System",
                "min_pressure": 0.5,
                "max_pressure": 10.0
            }
        }
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to control topics
            client.subscribe("iot/devices/+/control")
            logger.info("Subscribed to device control topics")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects"""
        self.connected = False
        if rc != 0:
            logger.warning("Unexpected disconnection from MQTT broker")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming control messages"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3:
                device_id = topic_parts[2]
                
                if device_id in self.devices:
                    command_data = json.loads(msg.payload.decode())
                    self.handle_device_command(device_id, command_data)
                    
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    def handle_device_command(self, device_id, command_data):
        """Handle device control commands"""
        action = command_data.get('action', '')
        value = command_data.get('value', '')
        
        logger.info(f"Received command for {device_id}: {action} = {value}")
        
        device_info = self.devices[device_id]
        
        # Simulate command execution
        if device_info["type"] == "pump":
            if action == "start":
                device_info["status"] = "running"
            elif action == "stop":
                device_info["status"] = "stopped"
            elif action == "flow_rate" and value:
                device_info["flow_rate"] = float(value)
                
        elif device_info["type"] == "valve":
            if action == "position" and value:
                position = int(value)
                if 0 <= position <= device_info["max_position"]:
                    device_info["position"] = position
        
        # Publish updated status
        self.publish_device_status(device_id, device_info)
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id="simple_iot_simulator")
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.connected
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
    
    def publish_device_status(self, device_id, device_info):
        """Publish device status"""
        if not self.connected:
            return
            
        status_data = {
            "device_id": device_id,
            "online": True,
            "type": device_info["type"],
            "location": device_info["location"],
            "firmware_version": "1.2.3",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add device-specific status
        if device_info["type"] == "pump":
            status_data["status"] = device_info["status"]
            status_data["flow_rate"] = device_info["flow_rate"]
        elif device_info["type"] == "valve":
            status_data["position"] = device_info["position"]
            status_data["max_position"] = device_info["max_position"]
        
        topic = f"iot/devices/{device_id}/status"
        self.client.publish(topic, json.dumps(status_data))
        logger.debug(f"Published status for {device_id}")
    
    def publish_sensor_data(self, device_id, device_info):
        """Publish sensor data"""
        if not self.connected:
            return
            
        sensor_data = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate realistic sensor data based on device type
        if device_info["type"] == "temperature_sensor":
            sensor_data["temperature"] = round(
                random.uniform(device_info["min_temp"], device_info["max_temp"]), 1
            )
            sensor_data["unit"] = "°C"
            
        elif device_info["type"] == "humidity_sensor":
            sensor_data["humidity"] = round(
                random.uniform(device_info["min_humidity"], device_info["max_humidity"]), 1
            )
            sensor_data["unit"] = "%"
            
        elif device_info["type"] == "pressure_sensor":
            sensor_data["pressure"] = round(
                random.uniform(device_info["min_pressure"], device_info["max_pressure"]), 2
            )
            sensor_data["unit"] = "bar"
            
        elif device_info["type"] == "pump":
            # Simulate pump metrics
            sensor_data["flow_rate"] = round(
                device_info["flow_rate"] + random.uniform(-10, 10), 1
            )
            sensor_data["power_consumption"] = round(random.uniform(2.5, 4.2), 1)
            sensor_data["vibration"] = round(random.uniform(0.1, 0.8), 2)
            
        elif device_info["type"] == "valve":
            # Simulate valve metrics
            sensor_data["position"] = device_info["position"]
            sensor_data["flow_rate"] = round(random.uniform(50, 200), 1)
        
        topic = f"iot/devices/{device_id}/data"
        self.client.publish(topic, json.dumps(sensor_data))
        logger.debug(f"Published sensor data for {device_id}")
    
    def simulate_alert(self):
        """Simulate random alerts"""
        if not self.connected:
            return
            
        alert_types = [
            {
                "level": "WARNING",
                "message": "Temperature threshold exceeded",
                "device_id": "temp_sensor_01"
            },
            {
                "level": "ERROR", 
                "message": "Pump malfunction detected",
                "device_id": "pump_01"
            },
            {
                "level": "INFO",
                "message": "Maintenance scheduled",
                "device_id": "valve_01"
            },
            {
                "level": "CRITICAL",
                "message": "Pressure system failure",
                "device_id": "pressure_sensor_01"
            }
        ]
        
        # Random chance to generate alert (5% per cycle)
        if random.random() < 0.05:
            alert = random.choice(alert_types)
            alert_data = {
                **alert,
                "timestamp": datetime.now().isoformat(),
                "source": "device"
            }
            
            self.client.publish("iot/alerts", json.dumps(alert_data))
            logger.info(f"Generated alert: {alert['level']} - {alert['message']}")
    
    def run_simulation(self):
        """Run the device simulation"""
        logger.info("Starting Simple IoT Device Simulator...")
        
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT broker")
            return
        
        self.running = True
        
        try:
            while self.running:
                # Publish status and data for all devices
                for device_id, device_info in self.devices.items():
                    self.publish_device_status(device_id, device_info)
                    self.publish_sensor_data(device_id, device_info)
                
                # Simulate alerts
                self.simulate_alert()
                
                # Wait before next cycle
                time.sleep(10)  # Publish every 10 seconds
                
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.running = False
            self.disconnect_mqtt()

def main():
    """Main function"""
    simulator = SimpleIoTDeviceSimulator()
    simulator.run_simulation()

if __name__ == "__main__":
    print("Simple IoT Device Simulator")
    print("This simulator creates virtual IoT devices for testing the Telegram bot")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    main()
