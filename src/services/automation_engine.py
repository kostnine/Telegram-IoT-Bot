"""
Automation Engine for IoT Rules and Scheduled Actions
Handles IF-THEN rules, smart alerts, and scheduled tasks
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from croniter import croniter
from src.services.data_storage import DataStorage

logger = logging.getLogger(__name__)

@dataclass
class Rule:
    """Represents an automation rule"""
    rule_id: str
    name: str
    description: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    task_id: str
    name: str
    schedule: str  # Cron expression
    action: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0

class AutomationEngine:
    def __init__(self, data_storage: DataStorage, mqtt_client=None):
        self.storage = data_storage
        self.mqtt_client = mqtt_client
        self.rules: Dict[str, Rule] = {}
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.action_handlers: Dict[str, Callable] = {}
        
        self._register_default_handlers()
        self._load_rules_from_db()
        self._load_scheduled_tasks_from_db()
    
    def _register_default_handlers(self):
        """Register default action handlers"""
        self.action_handlers.update({
            'send_alert': self._handle_send_alert,
            'control_device': self._handle_control_device,
            'send_telegram': self._handle_send_telegram,
            'log_event': self._handle_log_event
        })
    
    def add_rule(self, rule_id: str, name: str, description: str, 
                 condition: Dict[str, Any], action: Dict[str, Any]) -> bool:
        """Add a new automation rule"""
        try:
            rule = Rule(rule_id, name, description, condition, action)
            self.rules[rule_id] = rule
            
            # Save to database
            with self.storage.storage.connect(self.storage.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO automation_rules 
                    (rule_id, name, description, condition_json, action_json, enabled)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (rule_id, name, description, 
                      json.dumps(condition), json.dumps(action), rule.enabled))
                conn.commit()
            
            logger.info(f"Added automation rule: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add rule {rule_id}: {e}")
            return False
    
    def add_scheduled_task(self, task_id: str, name: str, schedule: str, 
                          action: Dict[str, Any]) -> bool:
        """Add a new scheduled task"""
        try:
            # Validate cron expression
            cron = croniter(schedule, datetime.now())
            next_run = cron.get_next(datetime)
            
            task = ScheduledTask(task_id, name, schedule, action, 
                               next_run=next_run)
            self.scheduled_tasks[task_id] = task
            
            # Save to database
            with self.storage.storage.connect(self.storage.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO scheduled_tasks 
                    (task_id, name, schedule, action_json, enabled, next_run)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, name, schedule, json.dumps(action), 
                      task.enabled, next_run))
                conn.commit()
            
            logger.info(f"Added scheduled task: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add scheduled task {task_id}: {e}")
            return False
    
    def create_threshold_rule(self, device_id: str, sensor_type: str, 
                             threshold: float, operator: str, 
                             alert_level: str = "WARNING") -> str:
        """Create a simple threshold-based rule"""
        rule_id = f"threshold_{device_id}_{sensor_type}_{threshold}"
        
        condition = {
            "type": "sensor_threshold",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "operator": operator,  # >, <, >=, <=, ==
            "threshold": threshold
        }
        
        action = {
            "type": "send_alert",
            "level": alert_level,
            "message": f"{sensor_type} {operator} {threshold} on {device_id}"
        }
        
        self.add_rule(
            rule_id,
            f"{sensor_type.title()} Threshold Alert",
            f"Alert when {sensor_type} {operator} {threshold}",
            condition,
            action
        )
        
        return rule_id
    
    def create_device_control_rule(self, trigger_device: str, trigger_condition: Dict,
                                  target_device: str, target_action: Dict) -> str:
        """Create an IF-THEN device control rule"""
        rule_id = f"control_{trigger_device}_{target_device}_{datetime.now().timestamp()}"
        
        condition = {
            "type": "device_condition",
            "device_id": trigger_device,
            **trigger_condition
        }
        
        action = {
            "type": "control_device",
            "device_id": target_device,
            **target_action
        }
        
        self.add_rule(
            rule_id,
            f"Auto Control: {trigger_device} → {target_device}",
            f"Control {target_device} based on {trigger_device} conditions",
            condition,
            action
        )
        
        return rule_id
    
    async def evaluate_rules(self, device_id: str, sensor_data: Dict[str, Any]):
        """Evaluate all rules against incoming sensor data"""
        try:
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                if await self._evaluate_condition(rule.condition, device_id, sensor_data):
                    await self._execute_action(rule.action, device_id, sensor_data)
                    
                    # Update rule statistics
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
                    
                    # Update database
                    with self.storage.storage.connect(self.storage.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE automation_rules 
                            SET last_triggered = ?, trigger_count = ?
                            WHERE rule_id = ?
                        """, (rule.last_triggered, rule.trigger_count, rule_id))
                        conn.commit()
                    
                    logger.info(f"Rule triggered: {rule.name}")
                    
        except Exception as e:
            logger.error(f"Error evaluating rules: {e}")
    
    async def _evaluate_condition(self, condition: Dict[str, Any], 
                                device_id: str, sensor_data: Dict[str, Any]) -> bool:
        """Evaluate a rule condition"""
        try:
            condition_type = condition.get('type')
            
            if condition_type == 'sensor_threshold':
                # Check if this condition applies to current device
                if condition.get('device_id') != device_id:
                    return False
                
                sensor_type = condition.get('sensor_type')
                operator = condition.get('operator')
                threshold = condition.get('threshold')
                
                if sensor_type not in sensor_data:
                    return False
                
                value = sensor_data[sensor_type]
                
                if operator == '>':
                    return value > threshold
                elif operator == '<':
                    return value < threshold
                elif operator == '>=':
                    return value >= threshold
                elif operator == '<=':
                    return value <= threshold
                elif operator == '==':
                    return value == threshold
                    
            elif condition_type == 'device_condition':
                # More complex device state conditions
                target_device = condition.get('device_id')
                if target_device != device_id:
                    return False
                
                # Check multiple conditions (AND logic)
                for key, expected_value in condition.items():
                    if key in ['type', 'device_id']:
                        continue
                    
                    if key not in sensor_data:
                        return False
                    
                    if isinstance(expected_value, dict):
                        # Handle range conditions
                        if 'min' in expected_value and sensor_data[key] < expected_value['min']:
                            return False
                        if 'max' in expected_value and sensor_data[key] > expected_value['max']:
                            return False
                    else:
                        if sensor_data[key] != expected_value:
                            return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            
        return False
    
    async def _execute_action(self, action: Dict[str, Any], 
                            device_id: str, sensor_data: Dict[str, Any]):
        """Execute a rule action"""
        try:
            action_type = action.get('type')
            
            if action_type in self.action_handlers:
                await self.action_handlers[action_type](action, device_id, sensor_data)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                
        except Exception as e:
            logger.error(f"Error executing action: {e}")
    
    async def _handle_send_alert(self, action: Dict[str, Any], 
                               device_id: str, sensor_data: Dict[str, Any]):
        """Handle alert sending action"""
        level = action.get('level', 'WARNING')
        message = action.get('message', 'Automated alert triggered')
        
        # Store alert in database
        self.storage.store_alert(device_id, 'automation_rule', level, message)
        
        logger.info(f"Alert generated: {level} - {message}")
    
    async def _handle_control_device(self, action: Dict[str, Any], 
                                   trigger_device: str, sensor_data: Dict[str, Any]):
        """Handle device control action"""
        target_device = action.get('device_id')
        command = action.get('command', {})
        
        if self.mqtt_client and target_device:
            try:
                self.mqtt_client.publish_device_command(target_device, command)
                logger.info(f"Sent command to {target_device}: {command}")
            except Exception as e:
                logger.error(f"Failed to send command to {target_device}: {e}")
    
    async def _handle_send_telegram(self, action: Dict[str, Any], 
                                  device_id: str, sensor_data: Dict[str, Any]):
        """Handle Telegram message sending"""
        # This would integrate with the Telegram bot
        message = action.get('message', 'Automation alert')
        logger.info(f"Telegram alert: {message}")
    
    async def _handle_log_event(self, action: Dict[str, Any], 
                              device_id: str, sensor_data: Dict[str, Any]):
        """Handle event logging"""
        message = action.get('message', 'Automated event logged')
        logger.info(f"Event log: {message} - Device: {device_id}")
    
    async def process_scheduled_tasks(self):
        """Process scheduled tasks that are due"""
        try:
            current_time = datetime.now()
            
            for task_id, task in self.scheduled_tasks.items():
                if not task.enabled or not task.next_run:
                    continue
                
                if current_time >= task.next_run:
                    # Execute task
                    await self._execute_action(task.action, None, {})
                    
                    # Update task statistics
                    task.last_run = current_time
                    task.run_count += 1
                    
                    # Calculate next run time
                    cron = croniter(task.schedule, current_time)
                    task.next_run = cron.get_next(datetime)
                    
                    # Update database
                    with self.storage.storage.connect(self.storage.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE scheduled_tasks 
                            SET last_run = ?, next_run = ?, run_count = ?
                            WHERE task_id = ?
                        """, (task.last_run, task.next_run, task.run_count, task_id))
                        conn.commit()
                    
                    logger.info(f"Scheduled task executed: {task.name}")
                    
        except Exception as e:
            logger.error(f"Error processing scheduled tasks: {e}")
    
    def _load_rules_from_db(self):
        """Load rules from database"""
        try:
            with self.storage.storage.connect(self.storage.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT rule_id, name, description, condition_json, action_json, 
                           enabled, last_triggered, trigger_count
                    FROM automation_rules
                """)
                
                for row in cursor.fetchall():
                    rule = Rule(
                        rule_id=row[0],
                        name=row[1],
                        description=row[2],
                        condition=json.loads(row[3]),
                        action=json.loads(row[4]),
                        enabled=bool(row[5]),
                        last_triggered=datetime.fromisoformat(row[6]) if row[6] else None,
                        trigger_count=row[7] or 0
                    )
                    self.rules[rule.rule_id] = rule
                    
                logger.info(f"Loaded {len(self.rules)} automation rules")
                
        except Exception as e:
            logger.error(f"Failed to load rules from database: {e}")
    
    def _load_scheduled_tasks_from_db(self):
        """Load scheduled tasks from database"""
        try:
            with self.storage.storage.connect(self.storage.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, name, schedule, action_json, enabled, 
                           last_run, next_run, run_count
                    FROM scheduled_tasks
                """)
                
                for row in cursor.fetchall():
                    task = ScheduledTask(
                        task_id=row[0],
                        name=row[1],
                        schedule=row[2],
                        action=json.loads(row[3]),
                        enabled=bool(row[4]),
                        last_run=datetime.fromisoformat(row[5]) if row[5] else None,
                        next_run=datetime.fromisoformat(row[6]) if row[6] else None,
                        run_count=row[7] or 0
                    )
                    self.scheduled_tasks[task.task_id] = task
                    
                logger.info(f"Loaded {len(self.scheduled_tasks)} scheduled tasks")
                
        except Exception as e:
            logger.error(f"Failed to load scheduled tasks from database: {e}")
    
    async def start_engine(self):
        """Start the automation engine"""
        self.running = True
        logger.info("Automation engine started")
        
        # Run scheduled task processor
        while self.running:
            await self.process_scheduled_tasks()
            await asyncio.sleep(60)  # Check every minute
    
    def stop_engine(self):
        """Stop the automation engine"""
        self.running = False
        logger.info("Automation engine stopped")
