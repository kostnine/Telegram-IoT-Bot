"""
Advanced IoT Commands module with Analytics and Automation features
Extends the basic IoT commands with data visualization and automation management
"""

import io
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from src.mqtt.client import SimpleMQTTClient
from src.services.data_storage import DataStorage
from src.services.analytics import IoTAnalytics
from src.services.automation_engine import AutomationEngine

logger = logging.getLogger(__name__)

class AdvancedIoTCommands:
    def __init__(self, mqtt_client: SimpleMQTTClient, data_storage: DataStorage, 
                 analytics: IoTAnalytics, automation_engine: AutomationEngine):
        self.mqtt_client = mqtt_client
        self.storage = data_storage
        self.analytics = analytics
        self.automation = automation_engine
    
    # Analytics Commands
    async def show_analytics_menu(self, query):
        """Show analytics options"""
        keyboard = [
            [InlineKeyboardButton("📊 Device Charts", callback_data='analytics_charts')],
            [InlineKeyboardButton("📈 Performance Report", callback_data='analytics_performance')],
            [InlineKeyboardButton("📋 Export Data", callback_data='analytics_export')],
            [InlineKeyboardButton("⏱️ Historical Trends", callback_data='analytics_trends')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = ("📊 Analytics Dashboard\n\n"
                "Choose an analytics option:")
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_device_charts_menu(self, query):
        """Show menu for device charts"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            try:
                await query.edit_message_text("No devices available for analytics.")
            except Exception:
                await query.message.reply_text("No devices available for analytics.")
            return
        
        keyboard = []
        for device_id in list(devices.keys())[:8]:  # Limit to 8 devices
            keyboard.append([InlineKeyboardButton(
                f"📊 {device_id}",
                callback_data=f'chart_{device_id}'
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='analytics_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = ("📊 Select Device for Charts\n\n"
                "Choose a device to view its sensor charts:")
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            # If we can't edit (e.g., message contains photo), send new message
            await query.message.reply_text(text, reply_markup=reply_markup)
    
    async def generate_device_chart(self, query, device_id: str):
        """Generate and send device chart"""
        try:
            await query.answer("Generating chart...")
            
            # Generate dashboard chart
            chart_buffer = self.analytics.generate_device_dashboard(device_id, hours=24)
            
            keyboard = [
                [InlineKeyboardButton("📊 Temperature", callback_data=f'chart_temp_{device_id}')],
                [InlineKeyboardButton("📊 Pressure", callback_data=f'chart_pressure_{device_id}')],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f'chart_{device_id}')],
                [InlineKeyboardButton("⬅️ Back", callback_data='analytics_charts')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_photo(
                photo=InputFile(chart_buffer, filename=f"{device_id}_dashboard.png"),
                caption=f"📊 Device Dashboard: {device_id} (24h)",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            await query.edit_message_text(f"❌ Error generating chart: {str(e)}")
    
    async def generate_sensor_chart(self, query, sensor_type: str, device_id: str):
        """Generate specific sensor chart"""
        try:
            await query.answer("Generating sensor chart...")
            
            chart_buffer = self.analytics.generate_sensor_chart(device_id, sensor_type, hours=24)
            
            keyboard = [
                [InlineKeyboardButton("📊 24h", callback_data=f'chart_{sensor_type}_{device_id}_24')],
                [InlineKeyboardButton("📊 7d", callback_data=f'chart_{sensor_type}_{device_id}_168')],
                [InlineKeyboardButton("⬅️ Back", callback_data=f'chart_{device_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_photo(
                photo=InputFile(chart_buffer, filename=f"{device_id}_{sensor_type}.png"),
                caption=f"📊 {sensor_type.title()} Chart: {device_id}",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error generating sensor chart: {e}")
            await query.edit_message_text(f"❌ Error generating sensor chart: {str(e)}")
    
    async def show_performance_report(self, query):
        """Show performance report"""
        try:
            report = self.analytics.generate_performance_report(hours=24)
            
            if not report:
                await query.edit_message_text("❌ No performance data available.")
                return
            
            text = "📈 Performance Report (24h)\n\n"
            
            summary = report.get('summary', {})
            text += f"📊 Summary:\n"
            text += f"   Total Devices: {summary.get('total_devices', 0)}\n"
            text += f"   Online: {summary.get('online_devices', 0)}\n"
            text += f"   Average Uptime: {summary.get('average_uptime', 0):.1f}%\n"
            text += f"   Total Alerts: {summary.get('total_alerts', 0)}\n\n"
            
            text += "🔍 Device Details:\n"
            for device_id, device_data in report.get('devices', {}).items():
                status = "🟢" if device_data.get('online') else "🔴"
                uptime = device_data.get('uptime_percentage', 0)
                alerts = device_data.get('alert_count', 0)
                text += f"{status} {device_id}: {uptime:.1f}% uptime, {alerts} alerts\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data='analytics_performance')],
                [InlineKeyboardButton("📋 Export Report", callback_data='export_performance')],
                [InlineKeyboardButton("⬅️ Back", callback_data='analytics_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            await query.edit_message_text(f"❌ Error generating report: {str(e)}")
    
    # Automation Commands
    async def show_automation_menu(self, query):
        """Show automation management menu"""
        keyboard = [
            [InlineKeyboardButton("📋 View Rules", callback_data='automation_rules')],
            [InlineKeyboardButton("➕ Create Rule", callback_data='automation_create')],
            [InlineKeyboardButton("⏰ Scheduled Tasks", callback_data='automation_schedule')],
            [InlineKeyboardButton("🔧 Quick Setup", callback_data='automation_quick')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = ("🤖 Automation Manager\n\n"
                "Manage your IoT automation rules and schedules:")
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_automation_rules(self, query):
        """Show existing automation rules"""
        try:
            rules = list(self.automation.rules.values())
            
            if not rules:
                text = "📋 No automation rules configured.\n\n"
                text += "Create your first rule to automate device control!"
            else:
                text = f"📋 Active Automation Rules ({len(rules)})\n\n"
                
                for rule in rules[:5]:  # Show first 5 rules
                    status = "✅" if rule.enabled else "❌"
                    text += f"{status} {rule.name}\n"
                    text += f"   Triggered: {rule.trigger_count} times\n"
                    if rule.last_triggered:
                        text += f"   Last: {rule.last_triggered.strftime('%m-%d %H:%M')}\n"
                    text += "\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Create Rule", callback_data='automation_create')],
                [InlineKeyboardButton("⚙️ Manage Rules", callback_data='automation_manage')],
                [InlineKeyboardButton("⬅️ Back", callback_data='automation_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(text, reply_markup=reply_markup)
            except Exception:
                await query.message.reply_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing automation rules: {e}")
            await query.edit_message_text(f"❌ Error loading rules: {str(e)}")
    
    async def show_quick_automation_setup(self, query):
        """Show quick automation setup options"""
        keyboard = [
            [InlineKeyboardButton("🌡️ Temperature Alert", callback_data='quick_temp_alert')],
            [InlineKeyboardButton("📊 Pressure Alert", callback_data='quick_pressure_alert')],
            [InlineKeyboardButton("⚡ Auto Pump Control", callback_data='quick_pump_control')],
            [InlineKeyboardButton("🕐 Scheduled Maintenance", callback_data='quick_maintenance')],
            [InlineKeyboardButton("⬅️ Back", callback_data='automation_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = ("🔧 Quick Automation Setup\n\n"
                "Choose a common automation pattern:")
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
    
    async def create_temperature_alert(self, query):
        """Create temperature threshold alert"""
        try:
            devices = self.mqtt_client.get_all_devices()
            temp_devices = [d for d in devices.keys() if 'temp' in d.lower() or 'sensor' in d.lower()]
            
            if not temp_devices:
                text = ("❌ No temperature sensors found.\n\n"
                    "Make sure temperature sensors are online.")
                reply_markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back", callback_data='automation_quick')
                ]])
                
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup)
                except Exception:
                    await query.message.reply_text(text, reply_markup=reply_markup)
                return
            
            # Create default temperature alert for first temperature device
            device_id = temp_devices[0]
            rule_id = self.automation.create_threshold_rule(
                device_id=device_id,
                sensor_type='temperature',
                threshold=30.0,
                operator='>',
                alert_level='WARNING'
            )
            
            text = f"✅ Temperature Alert Created!\n\n"
            text += f"Device: {device_id}\n"
            text += f"Alert when temperature > 30°C\n"
            text += f"Rule ID: {rule_id}\n\n"
            text += "You can modify thresholds in rule management."
            
            keyboard = [
                [InlineKeyboardButton("📋 View Rules", callback_data='automation_rules')],
                [InlineKeyboardButton("➕ Create Another", callback_data='automation_quick')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error creating temperature alert: {e}")
            await query.edit_message_text(f"❌ Error creating alert: {str(e)}")
    
    # Export Commands
    async def show_export_menu(self, query):
        """Show export options menu"""
        devices = self.mqtt_client.get_all_devices()
        
        if not devices:
            try:
                await query.edit_message_text("❌ No devices available for export.")
            except Exception:
                await query.message.reply_text("❌ No devices available for export.")
            return
        
        keyboard = []
        
        # Add device export options (limit to first 5 devices)
        device_list = list(devices.keys())[:5]
        for device_id in device_list:
            keyboard.append([
                InlineKeyboardButton(f"📊 {device_id} (CSV)", callback_data=f'export_csv_{device_id}'),
                InlineKeyboardButton(f"📋 {device_id} (Excel)", callback_data=f'export_excel_{device_id}')
            ])
        
        # Add performance report export
        keyboard.append([
            InlineKeyboardButton("📈 Performance Report", callback_data='export_performance')
        ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='analytics_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = ("📋 Data Export Menu\n\n"
                "Choose what to export:\n"
                "• CSV - Temperature sensor data\n"
                "• Excel - Complete device report\n"
                "• Performance - System overview")
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
    
    async def handle_export_callback(self, query, callback_data: str):
        """Handle export callback actions"""
        logger.info(f"Export callback received: {callback_data}")
        parts = callback_data.split('_')
        
        if len(parts) >= 3 and parts[1] in ['csv', 'excel']:
            format_type = parts[1]
            device_id = '_'.join(parts[2:])  # Handle device IDs with underscores
            logger.info(f"Exporting {format_type} for device {device_id}")
            await self.export_device_data(query, device_id, format_type)
        elif callback_data == 'export_performance':
            logger.info("Exporting performance report")
            await self.export_performance_report(query)
        else:
            logger.warning(f"Unknown export callback: {callback_data}")
    
    async def export_performance_report(self, query):
        """Export performance report as Excel"""
        try:
            await query.answer("Generating performance report...")
            
            # Generate performance data
            report = self.analytics.generate_performance_report(hours=24)
            
            if not report:
                await query.message.reply_text("❌ No performance data available for export.")
                return
            
            # Create Excel file with performance data
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = [{
                    'Metric': 'Total Devices',
                    'Value': report['summary'].get('total_devices', 0)
                }, {
                    'Metric': 'Online Devices', 
                    'Value': report['summary'].get('online_devices', 0)
                }, {
                    'Metric': 'Average Uptime (%)',
                    'Value': report['summary'].get('average_uptime', 0)
                }, {
                    'Metric': 'Total Alerts',
                    'Value': report['summary'].get('total_alerts', 0)
                }]
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # Device details sheet
                device_data = []
                for device_id, data in report.get('devices', {}).items():
                    device_data.append({
                        'Device ID': device_id,
                        'Online': data.get('online', False),
                        'Uptime (%)': data.get('uptime_percentage', 0),
                        'Alert Count': data.get('alert_count', 0)
                    })
                
                if device_data:
                    df_devices = pd.DataFrame(device_data)
                    df_devices.to_excel(writer, sheet_name='Device Details', index=False)
            
            excel_buffer.seek(0)
            
            await query.message.reply_document(
                document=InputFile(excel_buffer, filename="performance_report_24h.xlsx"),
                caption="📈 System Performance Report (24h)"
            )
            
        except Exception as e:
            logger.error(f"Error exporting performance report: {e}")
            await query.message.reply_text(f"❌ Error exporting performance report: {str(e)}")

    async def export_device_data(self, query, device_id: str, format: str = 'csv'):
        """Export device data"""
        try:
            logger.info(f"Starting export for device {device_id} in format {format}")
            await query.answer("Preparing export...")
            
            if format == 'csv':
                # Export temperature data as CSV
                csv_buffer = self.analytics.export_sensor_data_csv(device_id, 'temperature', hours=24)
                
                await query.message.reply_document(
                    document=InputFile(csv_buffer, filename=f"{device_id}_temperature_24h.csv"),
                    caption=f"📋 Temperature data for {device_id} (24h)"
                )
            
            elif format == 'excel':
                # Export comprehensive Excel report
                excel_buffer = self.analytics.export_device_report_excel(device_id, hours=24)
                
                await query.message.reply_document(
                    document=InputFile(excel_buffer, filename=f"{device_id}_report_24h.xlsx"),
                    caption=f"📊 Complete device report for {device_id} (24h)"
                )
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            await query.edit_message_text(f"❌ Error exporting data: {str(e)}")
    
    # Command Handlers
    async def handle_analytics_callback(self, query, callback_data: str):
        """Handle analytics-related callbacks"""
        if callback_data == 'analytics_menu':
            await self.show_analytics_menu(query)
        elif callback_data == 'analytics_charts':
            await self.show_device_charts_menu(query)
        elif callback_data == 'analytics_performance':
            await self.show_performance_report(query)
        elif callback_data == 'analytics_export':
            await self.show_export_menu(query)
        elif callback_data.startswith('export_'):
            await self.handle_export_callback(query, callback_data)
        elif callback_data.startswith('chart_'):
            parts = callback_data.split('_')
            if len(parts) == 2:  # chart_device_id
                device_id = parts[1]
                await self.generate_device_chart(query, device_id)
            elif len(parts) >= 3:  # chart_sensor_device or chart_sensor_device_hours
                sensor_type = parts[1]
                device_id = parts[2]
                hours = int(parts[3]) if len(parts) > 3 else 24
                await self.generate_sensor_chart(query, sensor_type, device_id)
    
    async def handle_automation_callback(self, query, callback_data: str):
        """Handle automation-related callbacks"""
        if callback_data == 'automation_menu':
            await self.show_automation_menu(query)
        elif callback_data == 'automation_rules':
            await self.show_automation_rules(query)
        elif callback_data == 'automation_quick':
            await self.show_quick_automation_setup(query)
        elif callback_data == 'quick_temp_alert':
            await self.create_temperature_alert(query)
        # Add more automation handlers as needed
