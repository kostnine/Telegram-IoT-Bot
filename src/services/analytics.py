"""
Analytics Module for IoT Data Analysis and Visualization
Generates charts, reports, and performance metrics
"""

import io
import csv
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd
from src.services.data_storage import DataStorage

logger = logging.getLogger(__name__)

class IoTAnalytics:
    def __init__(self, data_storage: DataStorage):
        self.storage = data_storage
        
        # Configure matplotlib for better charts
        plt.style.use('seaborn-v0_8')
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['font.size'] = 10
    
    def generate_sensor_chart(self, device_id: str, sensor_type: str, 
                            hours: int = 24) -> io.BytesIO:
        """Generate a chart showing sensor data trends"""
        try:
            # Get historical data
            data = self.storage.get_sensor_history(device_id, sensor_type, hours)
            
            if not data:
                return self._create_no_data_chart(f"No {sensor_type} data for {device_id}")
            
            # Parse data
            timestamps = [datetime.fromisoformat(str(row[0])) for row in data]
            values = [row[1] for row in data]
            unit = data[0][2] if data[0][2] else ""
            
            # Create chart
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(timestamps, values, linewidth=2, marker='o', markersize=4)
            
            # Format chart
            ax.set_title(f'{device_id} - {sensor_type.title()} Trend ({hours}h)', 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('Time')
            ax.set_ylabel(f'{sensor_type.title()} ({unit})')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            if hours <= 24:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to BytesIO
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Failed to generate sensor chart: {e}")
            return self._create_error_chart(f"Error generating chart: {str(e)}")
    
    def generate_device_dashboard(self, device_id: str, hours: int = 24) -> io.BytesIO:
        """Generate a comprehensive device dashboard with multiple metrics"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'Device Dashboard: {device_id} ({hours}h)', 
                        fontsize=16, fontweight='bold')
            
            # Temperature chart
            temp_data = self.storage.get_sensor_history(device_id, 'temperature', hours)
            if temp_data:
                timestamps = [datetime.fromisoformat(str(row[0])) for row in temp_data]
                values = [row[1] for row in temp_data]
                ax1.plot(timestamps, values, 'r-', linewidth=2)
                ax1.set_title('Temperature')
                ax1.set_ylabel('°C')
                ax1.grid(True, alpha=0.3)
            
            # Pressure chart
            pressure_data = self.storage.get_sensor_history(device_id, 'pressure', hours)
            if pressure_data:
                timestamps = [datetime.fromisoformat(str(row[0])) for row in pressure_data]
                values = [row[1] for row in pressure_data]
                ax2.plot(timestamps, values, 'b-', linewidth=2)
                ax2.set_title('Pressure')
                ax2.set_ylabel('bar')
                ax2.grid(True, alpha=0.3)
            
            # Flow rate chart
            flow_data = self.storage.get_sensor_history(device_id, 'flow_rate', hours)
            if flow_data:
                timestamps = [datetime.fromisoformat(str(row[0])) for row in flow_data]
                values = [row[1] for row in flow_data]
                ax3.plot(timestamps, values, 'g-', linewidth=2)
                ax3.set_title('Flow Rate')
                ax3.set_ylabel('L/min')
                ax3.grid(True, alpha=0.3)
            
            # Uptime pie chart
            uptime = self.storage.get_device_uptime(device_id, hours)
            downtime = 100 - uptime
            ax4.pie([uptime, downtime], labels=['Online', 'Offline'], 
                   colors=['green', 'red'], autopct='%1.1f%%')
            ax4.set_title(f'Uptime: {uptime:.1f}%')
            
            plt.tight_layout()
            
            # Save to BytesIO
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Failed to generate device dashboard: {e}")
            return self._create_error_chart(f"Error generating dashboard: {str(e)}")
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance metrics for all devices"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'period_hours': hours,
                'devices': {},
                'summary': {
                    'total_devices': 0,
                    'online_devices': 0,
                    'average_uptime': 0.0,
                    'total_alerts': 0
                }
            }
            
            # Get all unique devices from recent data
            with sqlite3.connect(self.storage.db_path) as conn:
                cursor = conn.cursor()
                
                start_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT DISTINCT device_id 
                    FROM device_status 
                    WHERE timestamp > ?
                """, (start_time,))
                
                devices = [row[0] for row in cursor.fetchall()]
                
                total_uptime = 0.0
                online_count = 0
                
                for device_id in devices:
                    uptime = self.storage.get_device_uptime(device_id, hours)
                    
                    # Count alerts for this device
                    cursor.execute("""
                        SELECT COUNT(*) FROM alert_history 
                        WHERE device_id = ? AND timestamp > ?
                    """, (device_id, start_time))
                    alert_count = cursor.fetchone()[0]
                    
                    # Get latest status
                    cursor.execute("""
                        SELECT online FROM device_status 
                        WHERE device_id = ? 
                        ORDER BY timestamp DESC LIMIT 1
                    """, (device_id,))
                    
                    latest_status = cursor.fetchone()
                    is_online = latest_status[0] if latest_status else False
                    
                    if is_online:
                        online_count += 1
                    
                    total_uptime += uptime
                    
                    report['devices'][device_id] = {
                        'uptime_percentage': uptime,
                        'online': is_online,
                        'alert_count': alert_count
                    }
                
                report['summary']['total_devices'] = len(devices)
                report['summary']['online_devices'] = online_count
                report['summary']['average_uptime'] = total_uptime / len(devices) if devices else 0.0
                
                # Total alerts across all devices
                cursor.execute("""
                    SELECT COUNT(*) FROM alert_history WHERE timestamp > ?
                """, (start_time,))
                report['summary']['total_alerts'] = cursor.fetchone()[0]
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {}
    
    def export_sensor_data_csv(self, device_id: str, sensor_type: str, 
                              hours: int = 24) -> io.BytesIO:
        """Export sensor data as CSV"""
        try:
            data = self.storage.get_sensor_history(device_id, sensor_type, hours)
            
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            
            # Write header
            writer.writerow(['Timestamp', 'Device ID', 'Sensor Type', 'Value', 'Unit'])
            
            # Write data
            for row in data:
                writer.writerow([row[0], device_id, sensor_type, row[1], row[2] or ''])
            
            # Convert to BytesIO
            csv_bytes = io.BytesIO()
            csv_bytes.write(csv_buffer.getvalue().encode('utf-8'))
            csv_bytes.seek(0)
            
            return csv_bytes
            
        except Exception as e:
            logger.error(f"Failed to export CSV data: {e}")
            return io.BytesIO()
    
    def export_device_report_excel(self, device_id: str, hours: int = 24) -> io.BytesIO:
        """Export comprehensive device report as Excel"""
        try:
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Temperature data
                temp_data = self.storage.get_sensor_history(device_id, 'temperature', hours)
                if temp_data:
                    df_temp = pd.DataFrame(temp_data, columns=['Timestamp', 'Temperature', 'Unit'])
                    df_temp.to_excel(writer, sheet_name='Temperature', index=False)
                
                # Pressure data
                pressure_data = self.storage.get_sensor_history(device_id, 'pressure', hours)
                if pressure_data:
                    df_pressure = pd.DataFrame(pressure_data, columns=['Timestamp', 'Pressure', 'Unit'])
                    df_pressure.to_excel(writer, sheet_name='Pressure', index=False)
                
                # Performance summary
                uptime = self.storage.get_device_uptime(device_id, hours)
                alerts = self.storage.get_recent_alerts(hours)
                device_alerts = [a for a in alerts if a.get('device_id') == device_id]
                
                summary_data = {
                    'Metric': ['Uptime %', 'Alert Count', 'Report Period (hours)'],
                    'Value': [uptime, len(device_alerts), hours]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            excel_buffer.seek(0)
            return excel_buffer
            
        except Exception as e:
            logger.error(f"Failed to export Excel report: {e}")
            return io.BytesIO()
    
    def _create_no_data_chart(self, message: str) -> io.BytesIO:
        """Create a chart showing no data available"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, message, horizontalalignment='center', 
                verticalalignment='center', fontsize=16, 
                transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer
    
    def _create_error_chart(self, error_message: str) -> io.BytesIO:
        """Create a chart showing error message"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, error_message, horizontalalignment='center', 
                verticalalignment='center', fontsize=14, color='red',
                transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        return img_buffer
