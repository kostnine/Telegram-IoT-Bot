"""
Configuration module for Telegram IoT Bot
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class for the IoT Bot"""
    
    # Telegram Bot Configuration
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # MQTT Configuration
    MQTT_BROKER: str = os.getenv('MQTT_BROKER', 'localhost')
    MQTT_PORT: int = int(os.getenv('MQTT_PORT', '1883'))
    MQTT_USERNAME: str = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD: str = os.getenv('MQTT_PASSWORD', '')
    MQTT_CLIENT_ID: str = os.getenv('MQTT_CLIENT_ID', 'telegram_iot_bot')
    
    # MQTT Topics
    MQTT_TOPICS: Dict[str, str] = field(default_factory=lambda: {
        'device_status': 'iot/devices/+/status',
        'device_data': 'iot/devices/+/data',
        'device_control': 'iot/devices/{}/control',
        'alerts': 'iot/alerts',
        'system_status': 'iot/system/status'
    })
    
    # Device Configuration
    DEVICE_TYPES: Dict[str, List[str]] = field(default_factory=lambda: {
        'sensor': ['temperature', 'humidity', 'pressure', 'vibration'],
        'actuator': ['pump', 'valve', 'motor', 'heater'],
        'controller': ['plc', 'gateway', 'hub']
    })
    
    # Alert Configuration
    ALERT_LEVELS: List[str] = field(default_factory=lambda: ['INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    
    # Data Storage
    DATA_RETENTION_HOURS: int = int(os.getenv('DATA_RETENTION_HOURS', '24'))
    MAX_DEVICES: int = int(os.getenv('MAX_DEVICES', '100'))
    
    # Bot Settings
    ADMIN_USER_IDS: List[int] = field(default_factory=lambda: [
        int(uid) for uid in os.getenv('ADMIN_USER_IDS', '').split(',') if uid.strip()
    ])
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        if not self.MQTT_BROKER:
            raise ValueError("MQTT_BROKER environment variable is required")
    
    def get_device_control_topic(self, device_id: str) -> str:
        """Get control topic for specific device"""
        return self.MQTT_TOPICS['device_control'].format(device_id)
    
    def is_admin_user(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.ADMIN_USER_IDS if self.ADMIN_USER_IDS else True
