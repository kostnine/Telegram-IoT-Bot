#!/usr/bin/env python3
"""
Telegram IoT Bot - Industrial IoT Integration via MQTT
Main application entry point
"""

import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from src.mqtt.client import SimpleMQTTClient as MQTTClient
from config.settings import Config
from src.handlers.iot_commands import IoTCommands
from src.services.data_storage import DataStorage
from src.services.analytics import IoTAnalytics
from src.services.automation_engine import AutomationEngine
from src.handlers.advanced_commands import AdvancedIoTCommands

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramIoTBot:
    def __init__(self):
        self.config = Config()
        self.mqtt_client = MQTTClient(self.config)
        
        # Initialize analytics and automation components
        self.data_storage = DataStorage("iot_data.db")
        self.analytics = IoTAnalytics(self.data_storage)
        self.automation_engine = AutomationEngine(self.data_storage, self.mqtt_client)
        
        # Connect components to MQTT client
        self.mqtt_client.set_data_storage(self.data_storage)
        self.mqtt_client.set_automation_engine(self.automation_engine)
        
        # Initialize command handlers
        self.iot_commands = IoTCommands(self.mqtt_client)
        self.advanced_commands = AdvancedIoTCommands(
            self.mqtt_client, self.data_storage, 
            self.analytics, self.automation_engine
        )
        
        self.application = None
        self.automation_task = None
        
        # Track users who started the bot (for push notifications)
        self.registered_users = set()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # Register user for push notifications
        chat_id = update.effective_chat.id
        self.registered_users.add(chat_id)
        logger.info(f"User {chat_id} registered for push notifications")
        
        # Get device count for display
        devices = self.mqtt_client.get_all_devices()
        online = len(self.mqtt_client.get_online_devices())
        total = len(devices)
        
        keyboard = [
            [InlineKeyboardButton(f"📱 Įrenginiai ({online}/{total} online)", callback_data='devices_list')],
            [
                InlineKeyboardButton("📈 Grafikai", callback_data='analytics_menu'),
                InlineKeyboardButton("🚨 Alertai", callback_data='all_alerts')
            ],
            [InlineKeyboardButton("🔄 Atnaujinti", callback_data='refresh_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🤖 *IoT Valdymo Centras*\n\n"
            f"📊 Įrenginiai: {online}/{total} online\n"
            "Pasirink veiksmą:"
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🔧 *Available Commands:*\n\n"
            "/start - Show main menu\n"
            "/status - Get all devices status\n"
            "/devices - List connected devices\n"
            "/control <device_id> <command> - Control device\n"
            "/monitor <device_id> - Monitor specific device\n"
            "/alerts - Show recent alerts\n"
            "/help - Show this help message\n\n"
            "*MQTT Topics:*\n"
            "• `iot/devices/+/status` - Device status\n"
            "• `iot/devices/+/data` - Sensor data\n"
            "• `iot/devices/+/control` - Device control\n"
            "• `iot/alerts` - System alerts"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'devices_list':
            await self.iot_commands.show_devices_list(query)
        elif query.data == 'refresh_main':
            await self.show_main_menu(query)
        elif query.data == 'device_status':
            await self.iot_commands.get_device_status(query)
        elif query.data == 'control_panel':
            await self.iot_commands.show_control_panel(query)
        elif query.data == 'monitoring':
            await self.iot_commands.show_monitoring(query)
        elif query.data == 'settings':
            await self.iot_commands.show_settings(query)
        elif query.data.startswith('d:'):
            # Direct device_id in callback
            device_id = query.data[2:]  # Remove 'd:' prefix
            await self.iot_commands.show_device_menu(query, device_id)
        elif query.data.startswith('analytics_'):
            await self.advanced_commands.handle_analytics_callback(query, query.data)
        elif query.data.startswith('automation_'):
            await self.advanced_commands.handle_automation_callback(query, query.data)
        elif query.data.startswith('export_'):
            await self.advanced_commands.handle_export_callback(query, query.data)
        elif query.data.startswith('chart_'):
            await self.advanced_commands.handle_analytics_callback(query, query.data)
        elif query.data.startswith('quick_'):
            await self.advanced_commands.handle_automation_callback(query, query.data)
        elif query.data == 'main_menu':
            await self.show_main_menu(query)
        elif query.data == 'device_details':
            await self.iot_commands.get_device_status(query)
        elif query.data == 'all_alerts':
            await self.iot_commands.show_all_alerts(query)
        elif query.data.startswith('control_'):
            device_id = query.data.replace('control_', '')
            await self.iot_commands.show_device_control(query, device_id)
        elif query.data.startswith('c:'):
            # Handle device command buttons (e.g., c:phone_xxx:beep)
            parts = query.data.split(':')
            if len(parts) >= 3:
                device_id = parts[1]
                command = parts[2]
                await self.iot_commands.execute_device_command(query, device_id, command)
        elif query.data.startswith('cmd_'):
            # Legacy format
            parts = query.data.replace('cmd_', '').rsplit('_', 1)
            if len(parts) == 2:
                device_id, command = parts
                await self.iot_commands.execute_device_command(query, device_id, command)
    
    async def show_main_menu(self, query):
        """Show main menu"""
        devices = self.mqtt_client.get_all_devices()
        online = len(self.mqtt_client.get_online_devices())
        total = len(devices)
        
        keyboard = [
            [InlineKeyboardButton(f"📱 Įrenginiai ({online}/{total} online)", callback_data='devices_list')],
            [
                InlineKeyboardButton("📈 Grafikai", callback_data='analytics_menu'),
                InlineKeyboardButton("🚨 Alertai", callback_data='all_alerts')
            ],
            [InlineKeyboardButton("🔄 Atnaujinti", callback_data='refresh_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 IoT Valdymo Centras\n\nPasirink veiksmą:",
            reply_markup=reply_markup
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        await self.iot_commands.get_all_devices_status(update)
    
    async def devices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /devices command"""
        await self.iot_commands.list_devices(update)
    
    async def control_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /control command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /control <device_id> <command>\n"
                "Example: /control pump_01 start"
            )
            return
        
        device_id = context.args[0]
        command = ' '.join(context.args[1:])
        await self.iot_commands.control_device(update, device_id, command)
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor command"""
        if len(context.args) < 1:
            await update.message.reply_text(
                "Usage: /monitor <device_id>\n"
                "Example: /monitor sensor_01"
            )
            return
        
        device_id = context.args[0]
        await self.iot_commands.monitor_device(update, device_id)
    
    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command"""
        await self.iot_commands.get_alerts(update)
    
    async def send_alert_notification(self, alert: dict):
        """Send push notification to all registered users"""
        if not self.application or not self.registered_users:
            return
        
        # Format alert message
        level = alert.get('level', 'INFO')
        message = alert.get('message', 'Unknown alert')
        device_id = alert.get('device_id', 'system')
        timestamp = alert.get('timestamp', '')
        
        # Emoji based on level
        emoji = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }.get(level, '📢')
        
        notification_text = (
            f"{emoji} *{level} ALERT*\n\n"
            f"📱 Įrenginys: `{device_id}`\n"
            f"💬 {message}\n"
            f"🕐 {timestamp[:19] if timestamp else 'now'}"
        )
        
        # Get device counts for main menu
        devices = self.mqtt_client.get_all_devices()
        online = len(self.mqtt_client.get_online_devices())
        total = len(devices)
        
        # Main menu keyboard
        keyboard = [
            [InlineKeyboardButton(f"📱 Įrenginiai ({online}/{total} online)", callback_data='devices_list')],
            [
                InlineKeyboardButton("📈 Grafikai", callback_data='analytics_menu'),
                InlineKeyboardButton("🚨 Alertai", callback_data='all_alerts')
            ],
            [InlineKeyboardButton("🔄 Atnaujinti", callback_data='refresh_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send to all registered users
        for chat_id in self.registered_users:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=notification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                logger.info(f"Alert notification sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to {chat_id}: {e}")
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("devices", self.devices_command))
        self.application.add_handler(CommandHandler("control", self.control_command))
        self.application.add_handler(CommandHandler("monitor", self.monitor_command))
        self.application.add_handler(CommandHandler("alerts", self.alerts_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def run(self):
        """Start the bot"""
        try:
            # Initialize MQTT client
            if not self.mqtt_client.connect():
                logger.warning("Failed to connect to MQTT broker - continuing without MQTT functionality")
            
            # Create Telegram application
            self.application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()
            
            # Setup handlers
            self.setup_handlers()
            
            logger.info("Starting Telegram IoT Bot...")
            
            # Start the automation engine
            self.automation_task = asyncio.create_task(self.automation_engine.start_engine())
            logger.info("Automation engine started")
            
            # Register alert callback for push notifications
            loop = asyncio.get_running_loop()
            self.mqtt_client.set_alert_callback(self.send_alert_notification, loop=loop)
            logger.info("Alert push notifications enabled")
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running with advanced analytics and automation. Press Ctrl+C to stop.")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
        finally:
            # Stop automation engine
            if self.automation_task:
                self.automation_engine.stop_engine()
                self.automation_task.cancel()
            
            if self.application:
                await self.application.stop()
            self.mqtt_client.disconnect()

async def main():
    """Main function"""
    bot = TelegramIoTBot()
    await bot.run()

if __name__ == "__main__":
    # Fix for Windows compatibility
    import sys
    # Add project root to path when running directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
