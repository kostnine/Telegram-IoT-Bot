#!/usr/bin/env python3
"""
Example IoT Device Simulator
Simulates IoT devices publishing data to MQTT broker for testing the Telegram bot
"""

import asyncio
import json
import random
import logging
from datetime import datetime
import aiomqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IoTDeviceSimulator:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
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
        self.running = False
    
    async def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.client = aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                client_id="iot_device_simulator"
            )
            await self.client.__aenter__()
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    async def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        if hasattr(self, 'client'):
            await self.client.__aexit__(None, None, None)
            logger.info("Disconnected from MQTT broker")
    
    async def publish_device_status(self, device_id, device_info):
        """Publish device status"""
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
        await self.client.publish(topic, json.dumps(status_data))
        logger.debug(f"Published status for {device_id}")
    
    async def publish_sensor_data(self, device_id, device_info):
        """Publish sensor data"""
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
        await self.client.publish(topic, json.dumps(sensor_data))
        logger.debug(f"Published sensor data for {device_id}")
    
    async def simulate_alert(self):
        """Simulate random alerts"""
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
            
            await self.client.publish("iot/alerts", json.dumps(alert_data))
            logger.info(f"Generated alert: {alert['level']} - {alert['message']}")
    
    async def listen_for_commands(self):
        """Listen for device control commands"""
        await self.client.subscribe("iot/devices/+/control")
        
        async for message in self.client.messages:
            try:
                topic_parts = str(message.topic).split('/')
                if len(topic_parts) >= 3:
                    device_id = topic_parts[2]
                    
                    if device_id in self.devices:
                        command_data = json.loads(message.payload.decode())
                        await self.handle_device_command(device_id, command_data)
                        
            except Exception as e:
                logger.error(f"Error processing command: {e}")
    
    async def handle_device_command(self, device_id, command_data):
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
        await self.publish_device_status(device_id, device_info)
        
        # Send confirmation
        response_data = {
            "device_id": device_id,
            "command_executed": True,
            "action": action,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"iot/devices/{device_id}/status"
        await self.client.publish(topic, json.dumps(response_data))
    
    async def run_simulation(self):
        """Run the device simulation"""
        logger.info("Starting IoT Device Simulator...")
        
        if not await self.connect_mqtt():
            return
        
        self.running = True
        
        # Start command listener task
        command_task = asyncio.create_task(self.listen_for_commands())
        
        try:
            while self.running:
                # Publish status for all devices
                for device_id, device_info in self.devices.items():
                    await self.publish_device_status(device_id, device_info)
                    await self.publish_sensor_data(device_id, device_info)
                
                # Simulate alerts
                await self.simulate_alert()
                
                # Wait before next cycle
                await asyncio.sleep(10)  # Publish every 10 seconds
                
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.running = False
            command_task.cancel()
            await self.disconnect_mqtt()

async def main():
    """Main function"""
    simulator = IoTDeviceSimulator()
    await simulator.run_simulation()

if __name__ == "__main__":
    print("IoT Device Simulator")
    print("This simulator creates virtual IoT devices for testing the Telegram bot")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    # Fix for Windows compatibility
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
