"""
Data Storage Module for IoT Historical Data
Handles storing and retrieving sensor data, device metrics, and analytics
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, db_path: str = "iot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sensor data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        sensor_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT,
                        location TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Device status table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS device_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        online BOOLEAN NOT NULL,
                        status_data TEXT, -- JSON data
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Alert history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT,
                        alert_type TEXT NOT NULL,
                        level TEXT NOT NULL, -- INFO, WARNING, ERROR, CRITICAL
                        message TEXT NOT NULL,
                        rule_id TEXT,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        metric_type TEXT NOT NULL, -- uptime, efficiency, etc.
                        value REAL NOT NULL,
                        period_start DATETIME NOT NULL,
                        period_end DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Automation rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS automation_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        condition_json TEXT NOT NULL, -- JSON condition
                        action_json TEXT NOT NULL, -- JSON action
                        enabled BOOLEAN DEFAULT TRUE,
                        last_triggered DATETIME,
                        trigger_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Scheduled tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        schedule TEXT NOT NULL, -- Cron expression
                        action_json TEXT NOT NULL, -- JSON action
                        enabled BOOLEAN DEFAULT TRUE,
                        last_run DATETIME,
                        next_run DATETIME,
                        run_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Maintenance schedules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_schedules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        maintenance_type TEXT NOT NULL,
                        description TEXT,
                        interval_days INTEGER NOT NULL,
                        last_maintenance DATETIME,
                        next_maintenance DATETIME NOT NULL,
                        priority TEXT DEFAULT 'MEDIUM',
                        completed BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""CREATE INDEX IF NOT EXISTS idx_sensor_data_device_timestamp 
                                 ON sensor_data (device_id, timestamp)""")
                cursor.execute("""CREATE INDEX IF NOT EXISTS idx_device_status_device_timestamp 
                                 ON device_status (device_id, timestamp)""")
                cursor.execute("""CREATE INDEX IF NOT EXISTS idx_alert_timestamp 
                                 ON alert_history (timestamp)""")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_sensor_data(self, device_id: str, timestamp: str, sensor_data: Dict[str, Any]):
        """Store sensor data from IoT devices"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Parse timestamp
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # Store each sensor reading
                for key, value in sensor_data.items():
                    if key in ['device_id', 'timestamp']:
                        continue
                    
                    # Determine sensor type and unit
                    sensor_type = key
                    unit = None
                    
                    if key == 'temperature':
                        unit = '°C'
                    elif key == 'humidity':
                        unit = '%'
                    elif key == 'pressure':
                        unit = 'bar'
                    elif key == 'flow_rate':
                        unit = 'L/min'
                    elif key == 'power_consumption':
                        unit = 'kW'
                    elif key == 'vibration':
                        unit = 'mm/s'
                    
                    if isinstance(value, (int, float)):
                        cursor.execute("""
                            INSERT INTO sensor_data 
                            (device_id, timestamp, sensor_type, value, unit)
                            VALUES (?, ?, ?, ?, ?)
                        """, (device_id, dt, sensor_type, float(value), unit))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store sensor data for {device_id}: {e}")
    
    def store_device_status(self, device_id: str, timestamp: str, status_data: Dict[str, Any]):
        """Store device status updates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                online = status_data.get('online', False)
                
                cursor.execute("""
                    INSERT INTO device_status 
                    (device_id, timestamp, online, status_data)
                    VALUES (?, ?, ?, ?)
                """, (device_id, dt, online, json.dumps(status_data)))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store device status for {device_id}: {e}")
    
    def store_alert(self, device_id: str, alert_type: str, level: str, 
                   message: str, rule_id: str = None):
        """Store alert/alarm data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO alert_history 
                    (device_id, alert_type, level, message, rule_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (device_id, alert_type, level, message, rule_id, datetime.now()))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    def get_sensor_history(self, device_id: str, sensor_type: str, 
                          hours: int = 24) -> List[Tuple]:
        """Get historical sensor data for analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                start_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT timestamp, value, unit
                    FROM sensor_data 
                    WHERE device_id = ? AND sensor_type = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                """, (device_id, sensor_type, start_time))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Failed to get sensor history: {e}")
            return []
    
    def get_device_uptime(self, device_id: str, hours: int = 24) -> float:
        """Calculate device uptime percentage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                start_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN online = 1 THEN 1 ELSE 0 END) as online_count
                    FROM device_status 
                    WHERE device_id = ? AND timestamp > ?
                """, (device_id, start_time))
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    return (result[1] / result[0]) * 100.0
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to calculate uptime for {device_id}: {e}")
            return 0.0
    
    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent alerts for dashboard"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                start_time = datetime.now() - timedelta(hours=hours)
                
                cursor.execute("""
                    SELECT device_id, alert_type, level, message, timestamp, acknowledged
                    FROM alert_history 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (start_time, limit))
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'device_id': row[0],
                        'alert_type': row[1],
                        'level': row[2],
                        'message': row[3],
                        'timestamp': row[4],
                        'acknowledged': bool(row[5])
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to manage database size"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Clean sensor data
                cursor.execute("DELETE FROM sensor_data WHERE created_at < ?", (cutoff_date,))
                
                # Clean device status (keep less frequent)
                cursor.execute("DELETE FROM device_status WHERE created_at < ?", (cutoff_date,))
                
                # Keep alerts longer (90 days)
                alert_cutoff = datetime.now() - timedelta(days=90)
                cursor.execute("DELETE FROM alert_history WHERE created_at < ?", (alert_cutoff,))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
