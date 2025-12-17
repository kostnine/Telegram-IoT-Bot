"""
MQTT Client for IoT device communication
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import aiomqtt
from config import Config

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[aiomqtt.Client] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.device_data: Dict[str, Dict] = {}
        self.alerts: list = []
        
    async def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = aiomqtt.Client(
                hostname=self.config.MQTT_BROKER,
                port=self.config.MQTT_PORT,
                username=self.config.MQTT_USERNAME if self.config.MQTT_USERNAME else None,
                password=self.config.MQTT_PASSWORD if self.config.MQTT_PASSWORD else None,
                client_id=self.config.MQTT_CLIENT_ID
            )
            
            await self.client.__aenter__()
            self.connected = True
            logger.info(f"Connected to MQTT broker at {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
            
            # Subscribe to topics
            await self._subscribe_to_topics()
            
            # Start message processing task
            asyncio.create_task(self._process_messages())
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            try:
                await self.client.__aexit__(None, None, None)
                self.connected = False
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    async def _subscribe_to_topics(self):
        """Subscribe to all configured MQTT topics"""
        topics = [
            self.config.MQTT_TOPICS['device_status'],
            self.config.MQTT_TOPICS['device_data'],
            self.config.MQTT_TOPICS['alerts'],
            self.config.MQTT_TOPICS['system_status']
        ]
        
        for topic in topics:
            await self.client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
    
    async def _process_messages(self):
        """Process incoming MQTT messages"""
        if not self.client:
            return
            
        try:
            async for message in self.client.messages:
                await self._handle_message(message)
        except Exception as e:
            logger.error(f"Error processing MQTT messages: {e}")
    
    async def _handle_message(self, message):
        """Handle incoming MQTT message"""
        try:
            topic = str(message.topic)
            payload = message.payload.decode()
            
            logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in message from topic {topic}")
                return
            
            # Route message based on topic
            if '/status' in topic:
                await self._handle_device_status(topic, data)
            elif '/data' in topic:
                await self._handle_device_data(topic, data)
            elif 'alerts' in topic:
                await self._handle_alert(data)
            elif 'system' in topic:
                await self._handle_system_status(data)
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
    async def _handle_device_status(self, topic: str, data: Dict[str, Any]):
        """Handle device status updates"""
        # Extract device ID from topic (iot/devices/device_id/status)
        parts = topic.split('/')
        if len(parts) >= 3:
            device_id = parts[2]
            
            if device_id not in self.device_data:
                self.device_data[device_id] = {}
            
            self.device_data[device_id].update({
                'status': data,
                'last_seen': datetime.now().isoformat(),
                'online': data.get('online', False)
            })
            
            logger.info(f"Updated status for device {device_id}: {data}")
    
    async def _handle_device_data(self, topic: str, data: Dict[str, Any]):
        """Handle device sensor data"""
        # Extract device ID from topic
        parts = topic.split('/')
        if len(parts) >= 3:
            device_id = parts[2]
            
            if device_id not in self.device_data:
                self.device_data[device_id] = {}
            
            if 'sensor_data' not in self.device_data[device_id]:
                self.device_data[device_id]['sensor_data'] = []
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            self.device_data[device_id]['sensor_data'].append(data)
            
            # Keep only recent data (last 100 readings)
            if len(self.device_data[device_id]['sensor_data']) > 100:
                self.device_data[device_id]['sensor_data'] = \
                    self.device_data[device_id]['sensor_data'][-100:]
            
            logger.debug(f"Updated sensor data for device {device_id}")
    
    async def _handle_alert(self, data: Dict[str, Any]):
        """Handle system alerts"""
        alert = {
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'level': data.get('level', 'INFO'),
            'message': data.get('message', ''),
            'device_id': data.get('device_id', ''),
            'source': data.get('source', 'system')
        }
        
        self.alerts.append(alert)
        
        # Keep only recent alerts (last 50)
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
        
        logger.info(f"New alert: {alert}")
    
    async def _handle_system_status(self, data: Dict[str, Any]):
        """Handle system status updates"""
        logger.info(f"System status update: {data}")
    
    async def publish_device_command(self, device_id: str, command: Dict[str, Any]):
        """Send command to specific device"""
        if not self.connected or not self.client:
            raise ConnectionError("MQTT client not connected")
        
        topic = self.config.get_device_control_topic(device_id)
        
        # Add timestamp and source to command
        command_data = {
            'timestamp': datetime.now().isoformat(),
            'source': 'telegram_bot',
            **command
        }
        
        payload = json.dumps(command_data)
        
        try:
            await self.client.publish(topic, payload)
            logger.info(f"Sent command to device {device_id}: {command}")
        except Exception as e:
            logger.error(f"Failed to send command to device {device_id}: {e}")
            raise
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a device"""
        return self.device_data.get(device_id, {}).get('status')
    
    def get_device_data(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get all data for a device"""
        return self.device_data.get(device_id)
    
    def get_all_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get data for all devices"""
        return self.device_data
    
    def get_recent_alerts(self, limit: int = 10) -> list:
        """Get recent alerts"""
        return self.alerts[-limit:] if self.alerts else []
    
    def get_online_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get only online devices"""
        return {
            device_id: data for device_id, data in self.device_data.items()
            if data.get('online', False)
        }
    
    def register_message_handler(self, topic_pattern: str, handler: Callable):
        """Register custom message handler for specific topic pattern"""
        self.message_handlers[topic_pattern] = handler
