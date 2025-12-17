#!/usr/bin/env python3
"""
Free PC System Monitor - Turn your computer into IoT device
No additional hardware required!
"""

import json
import time
import psutil
import platform
import socket
import subprocess
import ssl
import os
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to get additional PC sensors (optional)
try:
    import wmi  # Windows Management Instrumentation
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# Try LibreHardwareMonitor for better temperature reading
LHM_AVAILABLE = False
try:
    import clr
    import os as os_module
    lhm_path = os_module.path.join(os_module.path.dirname(__file__), 'LibreHardwareMonitorLib.dll')
    if os_module.path.exists(lhm_path):
        clr.AddReference(lhm_path)
        from LibreHardwareMonitor.Hardware import Computer
        LHM_AVAILABLE = True
except:
    pass

class FreePCMonitor:
    def __init__(self, device_id="free_pc_monitor", mqtt_broker="localhost", mqtt_port=1883,
                 mqtt_username=None, mqtt_password=None, use_tls=False):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.use_tls = use_tls
        
        # MQTT setup
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Set credentials if provided
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)
        
        # Enable TLS if configured
        if use_tls:
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        
        # WMI interface for Windows (if available)
        self.wmi_interface = None
        if WMI_AVAILABLE and platform.system() == "Windows":
            try:
                self.wmi_interface = wmi.WMI()
            except:
                pass
        
        # System info cache
        self.system_info = self.get_static_system_info()
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ PC Monitor connected to MQTT")
            
            # Subscribe to control commands
            client.subscribe(f"iot/devices/{self.device_id}/control")
            
            # Send initial status
            self.send_device_status()
        else:
            print(f"❌ Connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            print(f"📨 Command: {payload}")
            
            # Parse JSON command
            try:
                data = json.loads(payload)
                command = data.get('action', payload)
            except json.JSONDecodeError:
                command = payload  # Plain text command
            
            print(f"🎯 Executing: {command}")
            
            if command == "status":
                self.send_device_status()
            elif command == "full_report":
                self.send_detailed_system_report()
            elif command == "process_list":
                self.send_process_list()
            elif command == "network_test":
                self.run_network_test()
            elif command == "disk_check":
                self.check_disk_health()
            elif command == "temperature_check":
                self.check_temperatures()
            elif command == "cleanup":
                self.run_system_cleanup()
            elif command == "restart_warning":
                self.send_restart_warning()
            # PC Control commands
            elif command == "shutdown":
                self.shutdown_pc()
            elif command == "restart":
                self.restart_pc()
            elif command == "lock":
                self.lock_pc()
            elif command == "screen_off":
                self.screen_off()
            elif command == "sleep":
                self.sleep_pc()
                
        except Exception as e:
            print(f"❌ Command error: {e}")
    
    def get_static_system_info(self):
        """Get system information that doesn't change"""
        info = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "python_version": platform.python_version(),
            "total_ram_gb": round(psutil.virtual_memory().total / 1024**3, 2),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
        }
        
        # Get disk information
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / 1024**3, 2)
                })
            except:
                pass
        
        info["disks"] = disk_info
        return info
    
    def send_device_status(self):
        """Send current system status"""
        status_data = {
            "device_id": self.device_id,
            "online": True,
            "type": "pc_system_monitor",
            "location": f"PC - {self.system_info['hostname']}",
            "firmware_version": "Python Monitor v1.0",
            "timestamp": datetime.now().isoformat(),
            "system_info": self.system_info,
            "current_user": psutil.users()[0].name if psutil.users() else "Unknown",
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1)
        }
        
        topic = f"iot/devices/{self.device_id}/status"
        self.client.publish(topic, json.dumps(status_data, indent=2))
        print("📤 PC status sent")
    
    def send_system_metrics(self):
        """Send real-time system metrics"""
        timestamp = datetime.now().isoformat()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        
        metrics = [
            ("cpu_usage", cpu_percent, "%"),
            ("cpu_frequency", cpu_freq.current if cpu_freq else 0, "MHz"),
            ("memory_usage", psutil.virtual_memory().percent, "%"),
            ("memory_available_gb", round(psutil.virtual_memory().available / 1024**3, 2), "GB"),
        ]
        
        # Disk usage for each partition
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_percent = (usage.used / usage.total) * 100
                metrics.append((
                    f"disk_usage_{partition.device.replace(':', '').replace('\\\\', '')}",
                    round(disk_percent, 1),
                    "%"
                ))
            except:
                pass
        
        # Network I/O
        network = psutil.net_io_counters()
        metrics.extend([
            ("network_bytes_sent_mb", round(network.bytes_sent / 1024**2, 2), "MB"),
            ("network_bytes_recv_mb", round(network.bytes_recv / 1024**2, 2), "MB"),
        ])
        
        # Process count
        metrics.append(("process_count", len(psutil.pids()), "processes"))
        
        # Load average (Unix-like systems)
        try:
            load_avg = psutil.getloadavg()
            metrics.append(("load_average_1min", round(load_avg[0], 2), ""))
        except:
            pass
        
        # Send each metric
        topic = f"iot/devices/{self.device_id}/data"
        for sensor_type, value, unit in metrics:
            sensor_data = {
                "device_id": self.device_id,
                "sensor_type": sensor_type,
                "value": value,
                "unit": unit,
                "timestamp": timestamp
            }
            self.client.publish(topic, json.dumps(sensor_data))
        
        print(f"📊 Metrics sent - CPU: {cpu_percent}%, RAM: {psutil.virtual_memory().percent}%")
        
        # Check for alerts
        self.check_system_alerts(cpu_percent, psutil.virtual_memory().percent)
    
    def check_temperatures(self):
        """Check CPU/GPU temperatures using LibreHardwareMonitor or WMI"""
        temps_found = False
        
        # Try LibreHardwareMonitor first (more reliable)
        if LHM_AVAILABLE:
            try:
                computer = Computer()
                computer.IsCpuEnabled = True
                computer.IsGpuEnabled = True
                computer.Open()
                
                for hardware in computer.Hardware:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType.ToString() == "Temperature":
                            temp = sensor.Value
                            if temp is not None:
                                name = f"{hardware.HardwareType}_{sensor.Name}".replace(" ", "_").lower()
                                self.send_sensor_data(name, round(float(temp), 1), "°C")
                                temps_found = True
                                
                                if float(temp) > 85:
                                    self.send_alert(f"Aukšta temperatūra {sensor.Name}: {temp:.1f}°C", "CRITICAL")
                                elif float(temp) > 75:
                                    self.send_alert(f"Padidėjusi temperatūra {sensor.Name}: {temp:.1f}°C", "WARNING")
                    
                    for subhardware in hardware.SubHardware:
                        subhardware.Update()
                        for sensor in subhardware.Sensors:
                            if sensor.SensorType.ToString() == "Temperature":
                                temp = sensor.Value
                                if temp is not None:
                                    name = f"{subhardware.HardwareType}_{sensor.Name}".replace(" ", "_").lower()
                                    self.send_sensor_data(name, round(float(temp), 1), "°C")
                                    temps_found = True
                
                computer.Close()
                if temps_found:
                    return
            except Exception as e:
                print(f"⚠️ LHM error: {e}")
        
        # Fallback to WMI
        if self.wmi_interface:
            try:
                for temp_sensor in self.wmi_interface.MSAcpi_ThermalZoneTemperature():
                    temp_celsius = temp_sensor.CurrentTemperature / 10.0 - 273.15
                    self.send_sensor_data("cpu_temperature", round(temp_celsius, 1), "°C")
                    temps_found = True
                    
                    if temp_celsius > 80:
                        self.send_alert(f"Aukšta CPU temperatūra: {temp_celsius:.1f}°C", "CRITICAL")
            except:
                pass
        
        if not temps_found:
            print("⚠️ Temperatūros monitoringas neprieinamas")
    
    def send_sensor_data(self, sensor_type, value, unit):
        """Helper to send individual sensor data"""
        sensor_data = {
            "device_id": self.device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"iot/devices/{self.device_id}/data"
        self.client.publish(topic, json.dumps(sensor_data))
    
    def check_system_alerts(self, cpu_percent, memory_percent):
        """Check for system alerts"""
        if cpu_percent > 90:
            self.send_alert(f"Kritiškai aukšta CPU apkrova: {cpu_percent}%", "CRITICAL")
        elif cpu_percent > 80:
            self.send_alert(f"Aukšta CPU apkrova: {cpu_percent}%", "WARNING")
        
        if memory_percent > 95:
            self.send_alert(f"Kritiškai mažai RAM: {memory_percent}%", "CRITICAL")
        elif memory_percent > 85:
            self.send_alert(f"Aukštas RAM naudojimas: {memory_percent}%", "WARNING")
        
        # Check disk space
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_percent = (usage.used / usage.total) * 100
                
                if disk_percent > 95:
                    self.send_alert(f"Kritiškai mažai vietos diske {partition.device}: {disk_percent:.1f}%", "CRITICAL")
                elif disk_percent > 90:
                    self.send_alert(f"Mažai vietos diske {partition.device}: {disk_percent:.1f}%", "WARNING")
            except:
                pass
    
    def send_detailed_system_report(self):
        """Send comprehensive system report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_info,
            "current_metrics": {
                "cpu_percent": psutil.cpu_percent(),
                "memory": dict(psutil.virtual_memory()._asdict()),
                "disk_io": dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else None,
                "network_io": dict(psutil.net_io_counters()._asdict()),
            },
            "top_processes": self.get_top_processes(5)
        }
        
        # Send as special report
        topic = f"iot/devices/{self.device_id}/report"
        self.client.publish(topic, json.dumps(report, indent=2))
        self.send_alert("Sistemos ataskaita sugeneruota", "INFO")
    
    def get_top_processes(self, limit=5):
        """Get top processes by CPU usage"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage and return top N
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        return processes[:limit]
    
    def send_process_list(self):
        """Send list of running processes"""
        top_processes = self.get_top_processes(10)
        
        process_info = "Top 10 procesų pagal CPU naudojimą:\n"
        for proc in top_processes:
            process_info += f"• {proc['name']}: {proc['cpu_percent']:.1f}% CPU\n"
        
        self.send_alert(process_info, "INFO")
    
    def run_network_test(self):
        """Test network connectivity"""
        test_hosts = ["8.8.8.8", "google.com", "github.com"]
        results = []
        
        for host in test_hosts:
            try:
                # Simple ping test
                if platform.system() == "Windows":
                    result = subprocess.run(["ping", "-n", "1", host], 
                                          capture_output=True, text=True, timeout=5)
                else:
                    result = subprocess.run(["ping", "-c", "1", host], 
                                          capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    results.append(f"✅ {host}: OK")
                else:
                    results.append(f"❌ {host}: FAIL")
                    
            except subprocess.TimeoutExpired:
                results.append(f"⏱️ {host}: Timeout")
            except Exception as e:
                results.append(f"❌ {host}: {e}")
        
        network_report = "Tinklo ryšio testas:\n" + "\n".join(results)
        self.send_alert(network_report, "INFO")
    
    def check_disk_health(self):
        """Check disk health and usage"""
        disk_report = "Diskų būklės ataskaita:\n"
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_report += f"\n📀 {partition.device}:\n"
                disk_report += f"  • Tipas: {partition.fstype}\n"
                disk_report += f"  • Iš viso: {usage.total / 1024**3:.1f} GB\n"
                disk_report += f"  • Naudojama: {(usage.used / usage.total) * 100:.1f}%\n"
                disk_report += f"  • Laisvos: {usage.free / 1024**3:.1f} GB\n"
            except Exception as e:
                disk_report += f"❌ {partition.device}: {e}\n"
        
        self.send_alert(disk_report, "INFO")
    
    def run_system_cleanup(self):
        """Suggest system cleanup actions"""
        cleanup_suggestions = []
        
        # Check temporary files
        temp_dirs = []
        if platform.system() == "Windows":
            import os
            temp_dirs = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp')
            ]
        
        for temp_dir in temp_dirs:
            try:
                if temp_dir and os.path.exists(temp_dir):
                    temp_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                  for dirpath, dirnames, filenames in os.walk(temp_dir)
                                  for filename in filenames) / 1024**2  # MB
                    
                    if temp_size > 100:  # More than 100MB
                        cleanup_suggestions.append(f"🗑️ Temp failai: {temp_size:.0f} MB")
            except:
                pass
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            cleanup_suggestions.append("🧹 RAM išvalymas rekomenduojamas")
        
        if cleanup_suggestions:
            suggestion_text = "Sistemos valymo pasiūlymai:\n" + "\n".join(cleanup_suggestions)
        else:
            suggestion_text = "✅ Sistema švari, valymas nereikalingas"
        
        self.send_alert(suggestion_text, "INFO")
    
    def send_restart_warning(self):
        """Send restart warning with uptime info"""
        uptime_hours = (time.time() - psutil.boot_time()) / 3600
        
        if uptime_hours > 168:  # More than 1 week
            message = f"⚠️ Sistema veikia {uptime_hours:.0f} val. Rekomenduojamas perkrovimas"
            self.send_alert(message, "WARNING")
        else:
            message = f"✅ Uptime: {uptime_hours:.1f} val. Perkrovimas nereikalingas"
            self.send_alert(message, "INFO")
    
    def shutdown_pc(self):
        """Shutdown the PC"""
        print("⚠️ PC SHUTDOWN initiated!")
        self.send_alert("PC išjungiamas per 30 sek!", "WARNING")
        if platform.system() == "Windows":
            os.system("shutdown /s /t 30")
        else:
            os.system("shutdown -h +1")
    
    def restart_pc(self):
        """Restart the PC"""
        print("🔄 PC RESTART initiated!")
        self.send_alert("PC perkraunamas per 30 sek!", "WARNING")
        if platform.system() == "Windows":
            os.system("shutdown /r /t 30")
        else:
            os.system("shutdown -r +1")
    
    def lock_pc(self):
        """Lock the PC screen"""
        print("🔒 PC LOCK initiated!")
        self.send_alert("PC užrakintas", "INFO")
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        else:
            os.system("gnome-screensaver-command -l")
    
    def screen_off(self):
        """Turn off the PC screen"""
        print("📴 Screen OFF initiated!")
        self.send_alert("PC ekranas išjungtas", "INFO")
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
    
    def sleep_pc(self):
        """Put PC to sleep"""
        print("😴 PC SLEEP initiated!")
        self.send_alert("PC užmigdomas", "INFO")
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else:
            os.system("systemctl suspend")
    
    def send_alert(self, message, level="INFO"):
        """Send alert to MQTT"""
        alert_data = {
            "device_id": self.device_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "pc_monitor"
        }
        
        self.client.publish("iot/alerts", json.dumps(alert_data))
        print(f"🚨 Alert: {message}")
    
    def run_monitoring(self, interval=30):
        """Main monitoring loop"""
        try:
            print(f"🔄 Connecting to MQTT: {self.mqtt_broker}:{self.mqtt_port}")
            if self.use_tls:
                print("🔒 TLS/SSL enabled")
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
            
            print(f"🚀 PC Monitor started: {self.device_id}")
            print("📱 Check your Telegram bot for live PC metrics!")
            
            while True:
                self.send_system_metrics()
                
                # Check temperatures every few cycles (if available)
                if hasattr(self, '_temp_check_counter'):
                    self._temp_check_counter += 1
                else:
                    self._temp_check_counter = 0
                
                if self._temp_check_counter % 5 == 0:  # Every 5 cycles
                    self.check_temperatures()
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping PC Monitor...")
        except Exception as e:
            print(f"❌ Monitor error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    # Load configuration from .env file (same as bot uses)
    DEVICE_ID = f"pc_{socket.gethostname().lower()}"
    MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
    MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    USE_TLS = os.getenv('MQTT_USE_TLS', 'false').lower() == 'true'
    
    print("💻 Free PC IoT Monitor")
    print("======================")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Hostname: {socket.gethostname()}")
    print(f"Platform: {platform.platform()}")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"TLS: {'Enabled' if USE_TLS else 'Disabled'}")
    print()
    
    # Create and start monitor
    monitor = FreePCMonitor(
        device_id=DEVICE_ID,
        mqtt_broker=MQTT_BROKER,
        mqtt_port=MQTT_PORT,
        mqtt_username=MQTT_USERNAME,
        mqtt_password=MQTT_PASSWORD,
        use_tls=USE_TLS
    )
    monitor.run_monitoring(interval=20)  # Send data every 20 seconds
