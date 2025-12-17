#!/usr/bin/env python3
"""
Quick test to send real data to the IoT bot
Run this to simulate a real device without hardware
"""

import json
import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
        send_device_status(client)
    else:
        print(f"❌ Connection failed: {rc}")

def send_device_status(client):
    """Send real device status"""
    topic = "iot/devices/real_test_01/status"
    
    data = {
        "device_id": "real_test_01",
        "online": True,
        "type": "real_temperature_sensor",
        "location": "Jūsų Namai",
        "firmware_version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
    
    client.publish(topic, json.dumps(data))
    print(f"📤 Device status sent: {data}")

def send_real_data(client):
    """Send realistic sensor data"""
    topic = "iot/devices/real_test_01/data"
    timestamp = datetime.now().isoformat()
    
    # Realistic temperature (based on time of day)
    hour = datetime.now().hour
    base_temp = 18 + (hour - 6) * 0.8 if 6 <= hour <= 18 else 20
    temperature = base_temp + random.uniform(-2, 2)
    
    # Send temperature
    temp_data = {
        "device_id": "real_test_01",
        "sensor_type": "temperature",
        "value": round(temperature, 1),
        "unit": "°C",
        "timestamp": timestamp
    }
    client.publish(topic, json.dumps(temp_data))
    
    # Send humidity
    humidity = 45 + random.uniform(-10, 10)
    hum_data = {
        "device_id": "real_test_01",
        "sensor_type": "humidity",
        "value": round(humidity, 1),
        "unit": "%",
        "timestamp": timestamp
    }
    client.publish(topic, json.dumps(hum_data))
    
    print(f"📊 Real data sent: T={temp_data['value']}°C, H={hum_data['value']}%")
    
    # Send alert if temperature unusual
    if temperature > 25:
        send_alert(client, f"Aukšta temperatūra: {temp_data['value']}°C", "WARNING")

def send_alert(client, message, level):
    """Send real alert"""
    alert_data = {
        "device_id": "real_test_01",
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "source": "real_device"
    }
    
    client.publish("iot/alerts", json.dumps(alert_data))
    print(f"🚨 Alert sent: {message}")

def main():
    client = mqtt.Client(client_id="real_test_device")
    client.on_connect = on_connect
    
    try:
        print("🔄 Connecting to MQTT broker: localhost:1883")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        print("🚀 Real device test started")
        print("📱 Check your Telegram bot - you should see 'real_test_01' device!")
        
        # Send data every 15 seconds
        while True:
            send_real_data(client)
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping real device test...")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
