"""
Simple MQTT Client for Windows compatibility
Uses paho-mqtt with threading for better Windows support
"""

import json
import logging
import threading
import time
import asyncio
import ssl
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
import paho.mqtt.client as mqtt
from config.settings import Config

logger = logging.getLogger(__name__)

class SimpleMQTTClient:
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.device_data: Dict[str, Dict] = {}
        self.alerts: list = []
        self._stop_event = threading.Event()
        
        # Analytics and automation components
        self.data_storage = None
        self.automation_engine = None
        
        # Alert notification callback
        self.alert_callback = None
        self.admin_chat_ids = []
        self._main_loop = None
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=self.config.MQTT_CLIENT_ID)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # Set credentials if provided
            if self.config.MQTT_USERNAME and self.config.MQTT_PASSWORD:
                self.client.username_pw_set(
                    self.config.MQTT_USERNAME, 
                    self.config.MQTT_PASSWORD
                )
            
            # Enable TLS/SSL if configured (for cloud brokers like EMQX Cloud)
            if self.config.MQTT_USE_TLS:
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
                logger.info("TLS/SSL enabled for MQTT connection")
            
            # Connect to broker
            self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, 60)
            
            # Start the loop in a separate thread
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise ConnectionError("Failed to connect to MQTT broker within timeout")
                
            logger.info(f"Connected to MQTT broker at {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self.connected = True
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to topics
            topics = [
                self.config.MQTT_TOPICS['device_status'],
                self.config.MQTT_TOPICS['device_data'],
                self.config.MQTT_TOPICS['alerts'],
                self.config.MQTT_TOPICS['system_status']
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        self.connected = False
        if rc != 0:
            logger.warning("Unexpected disconnection from MQTT broker")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in message from topic {topic}")
                return
            
            # Route message based on topic
            if '/status' in topic:
                self._handle_device_status(topic, data)
            elif '/data' in topic:
                self._handle_device_data(topic, data)
            elif 'alerts' in topic:
                self._handle_alert(data)
            elif 'system' in topic:
                self._handle_system_status(data)
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
    def _handle_device_status(self, topic: str, data: Dict[str, Any]):
        """Handle device status updates"""
        # Extract device ID from topic (iot/devices/device_id/status)
        parts = topic.split('/')
        if len(parts) >= 3:
            device_id = parts[2]
            
            if device_id not in self.device_data:
                self.device_data[device_id] = {}
            
            timestamp = data.get('timestamp', datetime.now().isoformat())
            server_time = datetime.now().isoformat()  # Use SERVER time for last_seen
            
            self.device_data[device_id].update({
                'status': data,
                'last_seen': server_time,
                'online': True  # Device is online if sending status
            })
            
            # Store device status for analytics
            self._store_device_status_async(device_id, timestamp, data)
            
            logger.info(f"Updated status for device {device_id}: {data}")
    
    def _handle_device_data(self, topic: str, data: Dict[str, Any]):
        """Handle device sensor data"""
        # Extract device ID from topic
        parts = topic.split('/')
        if len(parts) >= 3:
            device_id = parts[2]
            
            # DEBUG: Log received sensor data
            sensor_type = data.get('sensor_type', 'unknown')
            value = data.get('value', '?')
            logger.info(f"📊 SENSOR DATA: {device_id} -> {sensor_type}: {value}")
            
            if device_id not in self.device_data:
                self.device_data[device_id] = {}
            
            if 'sensor_data' not in self.device_data[device_id]:
                self.device_data[device_id]['sensor_data'] = []
            
            # Add timestamp if not present
            timestamp = data.get('timestamp', datetime.now().isoformat())
            if 'timestamp' not in data:
                data['timestamp'] = timestamp
            
            # Mark device as online when receiving data - use SERVER time for last_seen
            server_time = datetime.now().isoformat()
            self.device_data[device_id]['online'] = True
            self.device_data[device_id]['last_seen'] = server_time
            
            self.device_data[device_id]['sensor_data'].append(data)
            
            # Keep only recent data (last 100 readings)
            if len(self.device_data[device_id]['sensor_data']) > 100:
                self.device_data[device_id]['sensor_data'] = \
                    self.device_data[device_id]['sensor_data'][-100:]
            
            # Store sensor data for analytics
            self._store_sensor_data_async(device_id, timestamp, data)
            
            # Evaluate automation rules
            self._evaluate_automation_rules_async(device_id, data)
            
            logger.info(f"✅ Stored sensor data for {device_id}, total: {len(self.device_data[device_id]['sensor_data'])}")
    
    def _handle_alert(self, data: Dict[str, Any]):
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
        
        # Send push notification for WARNING and CRITICAL alerts
        if alert['level'] in ['WARNING', 'CRITICAL', 'ERROR']:
            self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Dict[str, Any]):
        """Send push notification to registered users"""
        if self.alert_callback and self._main_loop:
            try:
                logger.info(f"🔔 Sending push notification for alert: {alert['level']}")
                # Schedule coroutine in the main event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.alert_callback(alert),
                    self._main_loop
                )
                # Don't wait for result to avoid blocking
                logger.info("🔔 Push notification scheduled")
            except Exception as e:
                logger.error(f"Failed to send alert notification: {e}")
    
    def set_alert_callback(self, callback: Callable, loop=None, chat_ids: list = None):
        """Set callback for alert notifications"""
        self.alert_callback = callback
        self._main_loop = loop
        if chat_ids:
            self.admin_chat_ids = chat_ids
        logger.info(f"Alert callback registered, loop: {loop is not None}")
    
    def _handle_system_status(self, data: Dict[str, Any]):
        """Handle system status updates"""
        logger.info(f"System status update: {data}")
    
    def publish_device_command(self, device_id: str, command):
        """Send command to specific device"""
        if not self.connected or not self.client:
            raise ConnectionError("MQTT client not connected")
        
        topic = self.config.get_device_control_topic(device_id)
        
        # Handle both string and dict commands
        if isinstance(command, str):
            command_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'telegram_bot',
                'action': command
            }
        else:
            command_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'telegram_bot',
                **command
            }
        
        payload = json.dumps(command_data)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent command to device {device_id}: {command}")
            else:
                raise Exception(f"Failed to publish message. Return code: {result.rc}")
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
    
    def is_device_online(self, device_id: str, timeout_seconds: int = 30) -> bool:
        """Check if device is online based on last_seen timestamp"""
        data = self.device_data.get(device_id, {})
        last_seen = data.get('last_seen')
        
        if not last_seen:
            return False
        
        try:
            now = datetime.now()
            if isinstance(last_seen, str):
                last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                if last_seen_dt.tzinfo:
                    last_seen_dt = last_seen_dt.replace(tzinfo=None)
            else:
                last_seen_dt = last_seen
            
            time_diff = (now - last_seen_dt).total_seconds()
            is_online = time_diff <= timeout_seconds
            
            # Update the online status in device_data
            data['online'] = is_online
            return is_online
        except Exception as e:
            logger.warning(f"Error checking online status for {device_id}: {e}")
            return False
    
    def get_online_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get only online devices (with timeout check)"""
        online_devices = {}
        
        for device_id, data in self.device_data.items():
            if self.is_device_online(device_id):
                online_devices[device_id] = data
        
        return online_devices
    
    def set_data_storage(self, data_storage):
        """Set the data storage component"""
        self.data_storage = data_storage
        logger.info("Data storage connected to MQTT client")
    
    def set_automation_engine(self, automation_engine):
        """Set the automation engine"""
        self.automation_engine = automation_engine
        logger.info("Automation engine connected to MQTT client")
    
    def _store_sensor_data_async(self, device_id: str, timestamp: str, sensor_data: Dict[str, Any]):
        """Store sensor data asynchronously"""
        if self.data_storage:
            try:
                self.data_storage.store_sensor_data(device_id, timestamp, sensor_data)
            except Exception as e:
                logger.error(f"Failed to store sensor data: {e}")
    
    def _store_device_status_async(self, device_id: str, timestamp: str, status_data: Dict[str, Any]):
        """Store device status asynchronously"""
        if self.data_storage:
            try:
                self.data_storage.store_device_status(device_id, timestamp, status_data)
            except Exception as e:
                logger.error(f"Failed to store device status: {e}")
    
    def get_admin_chat_ids(self) -> list:
        """Get registered admin chat IDs"""
        return self.admin_chat_ids
    
    def _evaluate_automation_rules_async(self, device_id: str, sensor_data: Dict[str, Any]):
        """Evaluate automation rules asynchronously"""
        if self.automation_engine:
            try:
                # Run in thread since we're in sync context but automation is async
                def run_async():
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    if loop.is_running():
                        # Create a task for the running loop
                        asyncio.create_task(
                            self.automation_engine.evaluate_rules(device_id, sensor_data)
                        )
                    else:
                        # Run the coroutine
                        loop.run_until_complete(
                            self.automation_engine.evaluate_rules(device_id, sensor_data)
                        )
                
                thread = threading.Thread(target=run_async)
                thread.start()
            except Exception as e:
                logger.error(f"Failed to evaluate automation rules: {e}")
