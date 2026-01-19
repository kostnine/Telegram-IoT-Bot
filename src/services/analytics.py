"""
Simple Analytics Module for IoT Data Analysis
Without matplotlib and pandas - only basic data analysis
"""

import io
import csv
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from src.services.data_storage import DataStorage

logger = logging.getLogger(__name__)

class IoTAnalytics:
    def __init__(self, data_storage: DataStorage):
        self.storage = data_storage
    
    def generate_sensor_chart(self, device_id: str, sensor_type: str, 
                            hours: int = 24) -> io.BytesIO:
        """Chart generation disabled - return text message"""
        img_buffer = io.BytesIO()
        message = f"📊 Chart generation disabled\n\nDevice: {device_id}\nSensor: {sensor_type}\nPeriod: {hours}h\n\nCharts are temporarily unavailable."
        img_buffer.write(message.encode())
        img_buffer.seek(0)
        return img_buffer
    
    def generate_device_dashboard(self, device_id: str, hours: int = 24) -> io.BytesIO:
        """Dashboard generation disabled - return text message"""
        img_buffer = io.BytesIO()
        message = f"📈 Dashboard generation disabled\n\nDevice: {device_id}\nPeriod: {hours}h\n\nDashboards are temporarily unavailable."
        img_buffer.write(message.encode())
        img_buffer.seek(0)
        return img_buffer
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate system performance report"""
        try:
            # Get all devices
            devices = self.storage.get_all_devices()
            
            # Calculate metrics
            total_devices = len(devices)
            online_devices = len([d for d in devices if d.get('online', False)])
            total_alerts = len(self.storage.get_recent_alerts(hours))
            
            # Device-specific data
            device_data = {}
            for device in devices:
                device_id = device.get('device_id', 'unknown')
                device_data[device_id] = {
                    'online': device.get('online', False),
                    'uptime_percentage': 100 if device.get('online', False) else 0,
                    'alert_count': 0
                }
            
            return {
                'summary': {
                    'total_devices': total_devices,
                    'online_devices': online_devices,
                    'average_uptime': 100 if online_devices > 0 else 0,
                    'total_alerts': total_alerts
                },
                'devices': device_data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return None
    
    def export_sensor_data(self, device_id: str, sensor_type: str, 
                          hours: int = 24, format: str = 'csv') -> io.BytesIO:
        """Export sensor data to CSV or JSON"""
        try:
            data = self.storage.get_sensor_history(device_id, sensor_type, hours)
            
            if not data:
                return io.BytesIO(b"No data available")
            
            buffer = io.BytesIO()
            
            if format.lower() == 'csv':
                writer = csv.writer(buffer)
                writer.writerow(['timestamp', 'value', 'unit'])
                writer.writerows(data)
            else:  # JSON
                json_data = [
                    {'timestamp': row[0], 'value': row[1], 'unit': row[2]}
                    for row in data
                ]
                buffer.write(json.dumps(json_data, indent=2).encode())
            
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Failed to export sensor data: {e}")
            return io.BytesIO(b"Export failed")
    
    def get_device_statistics(self, device_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistical summary for a device"""
        try:
            # Get temperature data
            temp_data = self.storage.get_sensor_history(device_id, 'temperature', hours)
            
            if not temp_data:
                return {'error': 'No data available'}
            
            values = [row[1] for row in temp_data]
            
            return {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'count': len(values),
                'latest': values[-1] if values else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get device statistics: {e}")
            return {'error': str(e)}
