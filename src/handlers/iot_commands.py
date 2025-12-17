"""
IoT Commands module for Telegram bot
Handles all IoT-related bot commands and interactions
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.mqtt.client import SimpleMQTTClient as MQTTClient

logger = logging.getLogger(__name__)

class IoTCommands:
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt_client = mqtt_client
        self._device_map = {}  # For short callback data
    
    def escape_markdown(self, text: str) -> str:
        """Escape special characters for Telegram Markdown"""
        if not isinstance(text, str):
            text = str(text)
        
        # Escape special Markdown characters
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    async def show_devices_list(self, query):
        """Show list of all devices"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            keyboard = [[InlineKeyboardButton("🏠 Grįžti", callback_data='main_menu')]]
            await query.edit_message_text(
                "📭 Nėra prijungtų įrenginių",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        text = "📱 Įrenginių sąrašas\n\n"
        keyboard = []
        
        for device_id, data in devices.items():
            online = data.get('online', False)
            status_icon = "🟢" if online else "🔴"
            device_type = data.get('status', {}).get('type', 'Unknown')
            
            # Shorten device_id for display
            short_id = device_id[:20] + "..." if len(device_id) > 20 else device_id
            
            text += f"{status_icon} {short_id}\n"
            text += f"   Tipas: {device_type}\n\n"
            
            # Use shortened device_id in callback (max 64 bytes)
            # Truncate device_id to fit in callback_data
            cb_device_id = device_id[:50]
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {short_id}",
                callback_data=f'd:{cb_device_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("🏠 Grįžti", callback_data='main_menu')])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_device_menu(self, query, device_id: str):
        """Show device details and commands"""
        device_data = self.mqtt_client.get_device_data(device_id)
        
        if not device_data:
            await query.edit_message_text(f"❌ Įrenginys '{device_id}' nerastas")
            return
        
        online = device_data.get('online', False)
        status_icon = "🟢 Online" if online else "🔴 Offline"
        device_status = device_data.get('status', {})
        device_type = device_status.get('type', 'Unknown')
        last_seen = device_data.get('last_seen', 'Niekada')
        if last_seen != 'Niekada':
            last_seen = last_seen[:19].replace('T', ' ')
        
        # Build device info text (no markdown to avoid underscore issues)
        text = f"📱 {device_id}\n\n"
        text += f"📊 Būsena: {status_icon}\n"
        text += f"🏷️ Tipas: {device_type}\n"
        text += f"⏰ Paskutinį kartą: {last_seen}\n\n"
        
        # Collect ALL sensor data from multiple sources
        recent_values = {}
        
        # 1. From sensor_data array (data topic messages)
        sensor_data = device_data.get('sensor_data', [])
        for reading in sensor_data[-50:]:
            sensor_type = reading.get('sensor_type', '')
            value = reading.get('value', '')
            unit = reading.get('unit', '')
            if sensor_type:
                if isinstance(value, float):
                    value = round(value, 2)
                # Skip 0 temperature readings (invalid)
                if 'temp' in sensor_type.lower() and value == 0:
                    continue
                recent_values[sensor_type] = f"{value} {unit}".strip()
        
        # 2. From status object (some devices send data in status)
        if device_status:
            sensor_fields = {
                # PC sensors
                'cpu_percent': ('CPU', '%'),
                'memory_percent': ('RAM', '%'),
                'disk_percent': ('Diskas', '%'),
                'temperature': ('Temperatūra', '°C'),
                'cpu_temp': ('CPU Temp', '°C'),
                'cpu_temperature': ('CPU Temp', '°C'),
                'gpu_temp': ('GPU Temp', '°C'),
                'network_sent': ('Siųsta', 'MB'),
                'network_recv': ('Gauta', 'MB'),
                'uptime': ('Veikimo laikas', ''),
                # Phone sensors
                'compass_heading': ('Kompasas', '°'),
                'acceleration': ('Akselerometras', 'm/s²'),
                'audio_level': ('Garso lygis', 'dB'),
                'battery_level': ('Baterija', '%'),
                'gps_latitude': ('GPS Lat', '°'),
                'gps_longitude': ('GPS Lon', '°'),
                'gyroscope': ('Giroskopas', 'rad/s'),
                'ambient_light': ('Šviesa', 'lux'),
            }
            for field, (name, unit) in sensor_fields.items():
                if field in device_status and device_status[field] is not None:
                    val = device_status[field]
                    if isinstance(val, float):
                        val = round(val, 2)
                    # Skip zero values for temperatures (invalid readings)
                    if 'temp' in field.lower() and val == 0:
                        continue
                    if val != 0 and str(val) != 'Laukiama...':  # Skip zero/waiting values
                        recent_values[field] = f"{val} {unit}".strip()
        
        # Show sensor data
        if recent_values:
            text += "📈 Sensorių duomenys:\n"
            for sensor, value in recent_values.items():
                nice_name = sensor.replace('_', ' ').title()
                text += f"   • {nice_name}: {value}\n"
        else:
            text += "📈 Sensorių duomenys: Laukiama...\n"
        
        # Show extra info (location, etc.)
        if device_status:
            extra_fields = ['location', 'ip', 'hostname', 'os', 'version', 'firmware_version']
            shown_extra = False
            for field in extra_fields:
                if field in device_status and device_status[field]:
                    if not shown_extra:
                        text += "\n📋 Papildoma info:\n"
                        shown_extra = True
                    nice_name = field.replace('_', ' ').title()
                    text += f"   • {nice_name}: {device_status[field]}\n"
        
        # Build command buttons based on device type
        keyboard = []
        
        # Short device_id for callbacks (max 64 bytes total)
        cb_id = device_id[:30]
        
        if device_type == 'smartphone_multisensor' or device_id.startswith('phone_'):
            # Phone commands
            keyboard.append([
                InlineKeyboardButton("🔊 Beep", callback_data=f'c:{cb_id}:beep'),
                InlineKeyboardButton("📳 Vibrate", callback_data=f'c:{cb_id}:vibrate')
            ])
            keyboard.append([
                InlineKeyboardButton("📍 Location", callback_data=f'c:{cb_id}:location'),
                InlineKeyboardButton("📡 Ping", callback_data=f'c:{cb_id}:ping')
            ])
            keyboard.append([
                InlineKeyboardButton("🔒 Lock", callback_data=f'c:{cb_id}:lock'),
                InlineKeyboardButton("🔓 Unlock", callback_data=f'c:{cb_id}:unlock')
            ])
            keyboard.append([
                InlineKeyboardButton("📴 Screen Off", callback_data=f'c:{cb_id}:screenoff')
            ])
        else:
            # PC commands
            keyboard.append([
                InlineKeyboardButton("🔒 Lock", callback_data=f'c:{cb_id}:lock'),
                InlineKeyboardButton("📴 Screen Off", callback_data=f'c:{cb_id}:screenoff')
            ])
            keyboard.append([
                InlineKeyboardButton("😴 Sleep", callback_data=f'c:{cb_id}:sleep'),
                InlineKeyboardButton("🔄 Restart", callback_data=f'c:{cb_id}:restart')
            ])
            keyboard.append([
                InlineKeyboardButton("⚠️ Shutdown", callback_data=f'c:{cb_id}:shutdown')
            ])
        
        keyboard.append([InlineKeyboardButton("🔄 Atnaujinti", callback_data=f'd:{cb_id}')])
        keyboard.append([InlineKeyboardButton("◀️ Įrenginiai", callback_data='devices_list')])
        keyboard.append([InlineKeyboardButton("🏠 Meniu", callback_data='main_menu')])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def get_device_status(self, query):
        """Get all devices status"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            await query.edit_message_text("📭 No devices connected")
            return
        
        status_text = "📊 Device Status Overview\n\n"
        
        online_count = 0
        offline_count = 0
        
        for device_id, data in devices.items():
            online = data.get('online', False)
            last_seen = data.get('last_seen', 'Never')
            
            if online:
                status_icon = "🟢"
                online_count += 1
            else:
                status_icon = "🔴"
                offline_count += 1
            
            status_text += f"{status_icon} {device_id}\n"
            status_text += f"   Last seen: {last_seen[:19] if last_seen != 'Never' else 'Never'}\n"
            
            # Add device type if available
            device_status = data.get('status', {})
            device_type = device_status.get('type', 'Unknown')
            status_text += f"   Type: {device_type}\n\n"
        
        status_text += f"📈 Summary: {online_count} online, {offline_count} offline"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data='device_status')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                status_text,
                reply_markup=reply_markup
            )
        except Exception:
            await query.message.reply_text(
                status_text,
                reply_markup=reply_markup
            )
    
    async def show_control_panel(self, query):
        """Show device control panel"""
        devices = self.mqtt_client.get_online_devices()
        
        if not devices:
            await query.edit_message_text(
                "🚫 No online devices available for control.\n\n"
                "Please check your device connections."
            )
            return
        
        keyboard = []
        for device_id in list(devices.keys())[:10]:  # Limit to 10 devices
            keyboard.append([InlineKeyboardButton(
                f"🎛️ {device_id}",
                callback_data=f'control_{device_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                "🔧 *Device Control Panel*\n\n"
                "Select a device to control:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception:
            await query.message.reply_text(
                "🔧 *Device Control Panel*\n\n"
                "Select a device to control:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def show_monitoring(self, query):
        """Show system monitoring overview"""
        from datetime import datetime
        
        devices = self.mqtt_client.get_all_devices()
        alerts = self.mqtt_client.get_recent_alerts(5)
        
        # Add timestamp to ensure content is always different
        current_time = datetime.now().strftime("%H:%M:%S")
        monitoring_text = f"📋 *System Monitoring* (Updated: {current_time})\n\n"
        
        # Device summary
        total_devices = len(devices)
        online_devices = len(self.mqtt_client.get_online_devices())
        
        monitoring_text += f"📊 *Device Summary:*\n"
        monitoring_text += f"   Total: {total_devices}\n"
        monitoring_text += f"   Online: {online_devices}\n"
        monitoring_text += f"   Offline: {total_devices - online_devices}\n\n"
        
        # Recent alerts
        if alerts:
            monitoring_text += "🚨 *Recent Alerts:*\n"
            for alert in alerts[-3:]:  # Show last 3 alerts
                level = alert.get('level', 'INFO')
                level_icon = "🔴" if level == 'CRITICAL' else "🟡" if level == 'WARNING' else "🔵"
                timestamp = alert.get('timestamp', '')[:16]  # Show date and time
                message = alert.get('message', 'No message')
                monitoring_text += f"{level_icon} {timestamp}: {message}\n"
        else:
            monitoring_text += "✅ *No recent alerts*\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Device Details", callback_data='device_details')],
            [InlineKeyboardButton("🚨 All Alerts", callback_data='all_alerts')],
            [InlineKeyboardButton("🔄 Refresh", callback_data='monitoring')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                monitoring_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            # If edit fails (same content), send new message
            await query.message.reply_text(
                monitoring_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def show_settings(self, query):
        """Show system overview with devices, status, and alerts"""
        from datetime import datetime
        
        # Get current devices
        devices = self.mqtt_client.get_all_devices()
        alerts = self.mqtt_client.get_recent_alerts(5)
        
        # System overview header
        settings_text = "⚙️ System Overview\n\n"
        
        # Real-time device status
        settings_text += "📊 Live Device Status:\n"
        if devices:
            online_count = sum(1 for d in devices.values() if d.get('online', False))
            settings_text += f"   📈 Total: {len(devices)} | Online: {online_count} | Offline: {len(devices) - online_count}\n\n"
            
            for device_id, data in devices.items():
                online = data.get('online', False)
                status_icon = "🟢" if online else "🔴"
                last_seen = data.get('last_seen', 'Never')
                if last_seen != 'Never':
                    last_seen = last_seen[:19].replace('T', ' ')
                
                settings_text += f"{status_icon} {device_id}\n"
                settings_text += f"   ⏰ Last seen: {last_seen}\n"
                
                # Show device type and location
                device_status = data.get('status', {})
                device_type = device_status.get('type', 'Unknown')
                location = device_status.get('location', 'Unknown')
                settings_text += f"   🏷️ Type: {device_type}\n"
                settings_text += f"   📍 Location: {location}\n"
                
                # Show latest sensor values if available - aggregate recent readings
                sensor_data = data.get('sensor_data', [])
                if sensor_data:
                    settings_text += f"   📊 Latest readings:\n"
                    # Get the most recent values for each sensor type
                    recent_values = {}
                    for reading in sensor_data[-20:]:  # Check last 20 readings
                        sensor_type = reading.get('sensor_type', '')
                        value = reading.get('value', '')
                        unit = reading.get('unit', '')
                        if sensor_type:
                            recent_values[sensor_type] = f"{value} {unit}".strip()
                    
                    # Display key metrics in a nice order
                    priority_sensors = ['cpu_usage', 'memory_usage', 'memory_available_gb', 
                                       'disk_usage_C', 'disk_usage_D', 'network_bytes_sent_mb',
                                       'network_bytes_recv_mb', 'process_count']
                    
                    displayed = set()
                    for sensor in priority_sensors:
                        if sensor in recent_values:
                            # Format sensor name nicely
                            nice_name = sensor.replace('_', ' ').title()
                            settings_text += f"     • {nice_name}: {recent_values[sensor]}\n"
                            displayed.add(sensor)
                    
                    # Show any other sensors not in priority list
                    for sensor, value in recent_values.items():
                        if sensor not in displayed and len(displayed) < 10:
                            nice_name = sensor.replace('_', ' ').title()
                            settings_text += f"     • {nice_name}: {value}\n"
                            displayed.add(sensor)
                
                settings_text += "\n"
        else:
            settings_text += "   📭 No devices connected\n\n"
        
        # Real-time alerts
        settings_text += "🚨 Recent Alerts:\n"
        if alerts:
            for alert in alerts[:3]:  # Show last 3 alerts
                timestamp = alert.get('timestamp', '')[:19].replace('T', ' ')
                level = alert.get('level', 'INFO')
                message = alert.get('message', '')
                device = alert.get('device_id', 'system')
                
                level_icon = "🔴" if level == 'CRITICAL' else "🟡" if level == 'WARNING' else "🔵"
                settings_text += f"{level_icon} {level} - {device}\n"
                settings_text += f"   📝 {message}\n"
                settings_text += f"   ⏰ {timestamp}\n\n"
        else:
            settings_text += "   ✅ No recent alerts\n\n"
        
        # MQTT Configuration (collapsed)
        settings_text += "🔧 MQTT Status:\n"
        connection_status = "🟢 Connected" if self.mqtt_client.connected else "🔴 Disconnected"
        settings_text += f"   Status: {connection_status}\n"
        settings_text += f"   Broker: {self.mqtt_client.config.MQTT_BROKER}:{self.mqtt_client.config.MQTT_PORT}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data='settings')],
            [InlineKeyboardButton("📊 Full Device Status", callback_data='device_status')],
            [InlineKeyboardButton("🚨 All Alerts", callback_data='all_alerts')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                settings_text,
                reply_markup=reply_markup
            )
        except Exception:
            # If edit fails, send new message
            await query.message.reply_text(
                settings_text,
                reply_markup=reply_markup
            )
    
    async def get_all_devices_status(self, update: Update):
        """Handle /status command"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            await update.message.reply_text(
                "📭 No devices found. Make sure your IoT devices are connected."
            )
            return
        
        status_text = "📊 *All Devices Status:*\n\n"
        
        for device_id, data in devices.items():
            online = data.get('online', False)
            status_icon = "🟢" if online else "🔴"
            
            status_text += f"{status_icon} *{device_id}*\n"
            
            # Device status details
            device_status = data.get('status', {})
            for key, value in device_status.items():
                if key != 'online':
                    escaped_key = self.escape_markdown(str(key))
                    escaped_value = self.escape_markdown(str(value))
                    status_text += f"   {escaped_key}: {escaped_value}\n"
            
            status_text += "\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def list_devices(self, update: Update):
        """Handle /devices command"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            await update.message.reply_text("📭 No devices found.")
            return
        
        device_list = "📱 *Connected Devices:*\n\n"
        
        for device_id, data in devices.items():
            online = data.get('online', False)
            status_icon = "🟢" if online else "🔴"
            device_type = data.get('status', {}).get('type', 'Unknown')
            last_seen = data.get('last_seen', 'Never')
            
            device_list += f"{status_icon} *{device_id}*\n"
            device_list += f"   Type: {device_type}\n"
            device_list += f"   Last seen: {last_seen[:19] if last_seen != 'Never' else 'Never'}\n\n"
        
        await update.message.reply_text(device_list, parse_mode='Markdown')
    
    async def control_device(self, update: Update, device_id: str, command: str):
        """Handle device control command"""
        try:
            # Check if device exists and is online
            device_data = self.mqtt_client.get_device_data(device_id)
            if not device_data:
                await update.message.reply_text(f"❌ Device '{device_id}' not found.")
                return
            
            if not device_data.get('online', False):
                await update.message.reply_text(f"🔴 Device '{device_id}' is offline.")
                return
            
            # Handle simple control commands (phone + PC)
            simple_commands = ['ping', 'vibrate', 'beep', 'location', 'lock', 'unlock', 'screen_off', 'screen_on',
                              'shutdown', 'restart', 'sleep', 'status', 'full_report']
            if command in simple_commands:
                self.mqtt_client.publish_device_command(device_id, command)
                await update.message.reply_text(f"✅ Komanda '{command}' išsiųsta")
                return
            
            # Parse command (simple format: action=value)
            command_data = {}
            if '=' in command:
                parts = command.split('=')
                command_data['action'] = parts[0].strip()
                command_data['value'] = parts[1].strip()
            else:
                command_data['action'] = command.strip()
            
            # Send command via MQTT
            self.mqtt_client.publish_device_command(device_id, command_data)
            
            await update.message.reply_text(
                f"✅ Command sent to device '{device_id}':\n"
                f"Action: {command_data.get('action')}\n"
                f"Value: {command_data.get('value', 'N/A')}"
            )
            
        except Exception as e:
            logger.error(f"Error controlling device {device_id}: {e}")
            await update.message.reply_text(f"❌ Error sending command: {str(e)}")
    
    async def monitor_device(self, update: Update, device_id: str):
        """Handle device monitoring command"""
        device_data = self.mqtt_client.get_device_data(device_id)
        
        if not device_data:
            await update.message.reply_text(f"❌ Device '{device_id}' not found.")
            return
        
        monitoring_text = f"📊 *Monitoring: {device_id}*\n\n"
        
        # Device status
        online = device_data.get('online', False)
        status_icon = "🟢" if online else "🔴"
        monitoring_text += f"Status: {status_icon} {'Online' if online else 'Offline'}\n"
        
        # Last seen
        last_seen = device_data.get('last_seen', 'Never')
        monitoring_text += f"Last seen: {last_seen[:19] if last_seen != 'Never' else 'Never'}\n\n"
        
        # Device status details
        device_status = device_data.get('status', {})
        if device_status:
            monitoring_text += "*Device Status:*\n"
            for key, value in device_status.items():
                if key != 'online':
                    monitoring_text += f"   {key}: {value}\n"
            monitoring_text += "\n"
        
        # Recent sensor data
        sensor_data = device_data.get('sensor_data', [])
        if sensor_data:
            monitoring_text += "*Recent Sensor Data:*\n"
            for reading in sensor_data[-3:]:  # Show last 3 readings
                timestamp = reading.get('timestamp', '')[:19]
                monitoring_text += f"   {timestamp}:\n"
                for key, value in reading.items():
                    if key != 'timestamp':
                        monitoring_text += f"     {key}: {value}\n"
                monitoring_text += "\n"
        
        await update.message.reply_text(monitoring_text, parse_mode='Markdown')
    
    async def get_alerts(self, update: Update):
        """Handle /alerts command"""
        alerts = self.mqtt_client.get_recent_alerts(10)
        
        if not alerts:
            await update.message.reply_text("✅ No recent alerts.")
            return
        
        alerts_text = "🚨 *Recent Alerts:*\n\n"
        
        for alert in reversed(alerts):  # Show newest first
            level_icon = self._get_alert_icon(alert.get('level', 'INFO'))
            timestamp = alert.get('timestamp', '')[:19]
            message = alert.get('message', 'No message')
            device_id = alert.get('device_id', '')
            source = alert.get('source', 'system')
            
            alerts_text += f"{level_icon} *{alert.get('level', 'INFO')}*\n"
            alerts_text += f"   Time: {timestamp}\n"
            alerts_text += f"   Message: {message}\n"
            if device_id:
                alerts_text += f"   Device: {device_id}\n"
            alerts_text += f"   Source: {source}\n\n"
        
        await update.message.reply_text(alerts_text, parse_mode='Markdown')
    
    def _get_alert_icon(self, level: str) -> str:
        """Get icon for alert level"""
        icons = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        return icons.get(level.upper(), 'ℹ️')
    
    async def show_device_control(self, query, device_id: str):
        """Show control options for a specific device"""
        device_data = self.mqtt_client.get_device_data(device_id)
        
        if not device_data:
            await query.edit_message_text(f"❌ Device '{device_id}' not found.")
            return
        
        device_status = device_data.get('status', {})
        device_type = device_status.get('type', 'Unknown')
        online = device_data.get('online', False)
        status_icon = "🟢" if online else "🔴"
        
        text = f"🎛️ Device Control: {device_id}\n\n"
        text += f"Status: {status_icon} {'Online' if online else 'Offline'}\n"
        text += f"Type: {device_type}\n"
        text += f"Location: {device_status.get('location', 'Unknown')}\n\n"
        
        keyboard = []
        
        # Add device-specific controls based on type
        if device_type == 'pump':
            keyboard.append([
                InlineKeyboardButton("▶️ Start", callback_data=f'cmd_{device_id}_start'),
                InlineKeyboardButton("⏹️ Stop", callback_data=f'cmd_{device_id}_stop')
            ])
        elif device_type == 'valve':
            keyboard.append([
                InlineKeyboardButton("🔓 Open", callback_data=f'cmd_{device_id}_open'),
                InlineKeyboardButton("🔒 Close", callback_data=f'cmd_{device_id}_close')
            ])
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f'control_{device_id}')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='control_panel')])
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_all_alerts(self, query):
        """Show all alerts via callback query"""
        alerts = self.mqtt_client.get_recent_alerts(10)
        
        if not alerts:
            text = "✅ No recent alerts."
        else:
            text = "🚨 Recent Alerts:\n\n"
            for alert in reversed(alerts):
                level_icon = self._get_alert_icon(alert.get('level', 'INFO'))
                timestamp = alert.get('timestamp', '')[:19]
                message = alert.get('message', 'No message')
                device_id = alert.get('device_id', '')
                
                text += f"{level_icon} {alert.get('level', 'INFO')}\n"
                text += f"   Time: {timestamp}\n"
                text += f"   Message: {message}\n"
                if device_id:
                    text += f"   Device: {device_id}\n"
                text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data='all_alerts')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def execute_device_command(self, query, device_id: str, command: str):
        """Execute a device command and show result"""
        try:
            # Check if device exists and is online
            device_data = self.mqtt_client.get_device_data(device_id)
            if not device_data:
                await query.edit_message_text(f"❌ Device '{device_id}' not found.")
                return
            
            if not device_data.get('online', False):
                await query.edit_message_text(f"🔴 Device '{device_id}' is offline.")
                return
            
            # Map command to MQTT command format
            command_data = {}
            if command == 'start':
                command_data = {'action': 'start'}
            elif command == 'stop':
                command_data = {'action': 'stop'}
            elif command == 'open':
                command_data = {'action': 'position', 'value': '100'}
            elif command == 'close':
                command_data = {'action': 'position', 'value': '0'}
            else:
                command_data = {'action': command}
            
            # Send command via MQTT
            self.mqtt_client.publish_device_command(device_id, command_data)
            
            # Show success message
            device_status = device_data.get('status', {})
            device_type = device_status.get('type', 'Unknown')
            
            text = f"✅ Komanda išsiųsta: {command}\n"
            text += f"📱 Įrenginys: {device_id}"
            
            # Short device_id for callback
            cb_id = device_id[:30]
            keyboard = [
                [InlineKeyboardButton("◀️ Grįžti į įrenginį", callback_data=f'd:{cb_id}')],
                [InlineKeyboardButton("🏠 Meniu", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error executing command {command} on device {device_id}: {e}")
            await query.edit_message_text(
                f"❌ Error executing command: {str(e)}\n\n"
                "Please try again or check device status.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Retry", callback_data=f'control_{device_id}'),
                    InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')
                ]])
            )
