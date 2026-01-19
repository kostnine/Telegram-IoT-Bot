#!/usr/bin/env python3
""" 
Tuya Smart Bulb -> MQTT Bridge

Listens for MQTT control commands and controls a Tuya Wi-Fi bulb locally via LAN.
Publishes device status back to MQTT.

Control topic: iot/devices/<device_id>/control
Status topic:  iot/devices/<device_id>/status

Requires:
- tinytuya
- paho-mqtt
- python-dotenv
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import tinytuya
from dotenv import load_dotenv
from paho.mqtt.client import Client as MQTTClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TuyaBulbBridge:
    def __init__(self):
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_username = os.getenv("MQTT_USERNAME", "")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "")
        self.mqtt_use_tls = os.getenv("MQTT_USE_TLS", "false").lower() == "true"

        self.tuya_device_id = os.getenv("TUYA_DEVICE_ID", "").strip()
        self.tuya_host = os.getenv("TUYA_HOST", "").strip()
        self.tuya_local_key = os.getenv("TUYA_LOCAL_KEY", "").strip()
        self.tuya_version = os.getenv("TUYA_VERSION", "3.3").strip()

        self.device_id = os.getenv("TUYA_MQTT_DEVICE_ID", "smart_bulb_01").strip()

        if not self.tuya_device_id:
            raise ValueError("TUYA_DEVICE_ID is required")
        if not self.tuya_host:
            raise ValueError("TUYA_HOST is required")
        if not self.tuya_local_key:
            raise ValueError("TUYA_LOCAL_KEY is required")

        self.status_topic = f"iot/devices/{self.device_id}/status"
        self.control_topic = f"iot/devices/{self.device_id}/control"

        self._lock = threading.Lock()
        self._connected = False

        self._power_on = False
        self._red = 255
        self._green = 255
        self._blue = 255
        self._brightness = 100

        self._dp_power: Optional[int] = None
        self._dp_brightness: Optional[int] = None
        self._dp_color: Optional[int] = None

        self._tuya = tinytuya.BulbDevice(self.tuya_device_id, self.tuya_host, self.tuya_local_key)
        self._tuya.set_version(float(self.tuya_version))
        # Make network behavior more predictable on Windows and avoid long hangs
        try:
            self._tuya.set_socketPersistent(True)
        except Exception:
            pass
        try:
            self._tuya.set_socketTimeout(3)
        except Exception:
            pass
        try:
            self._tuya.set_socketRetryLimit(2)
        except Exception:
            pass
        try:
            self._tuya.set_socketRetryDelay(0.2)
        except Exception:
            pass

        self._mqtt = MQTTClient(client_id=f"{self.device_id}_bridge")
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

    def connect(self) -> bool:
        try:
            if self.mqtt_username or self.mqtt_password:
                self._mqtt.username_pw_set(self.mqtt_username, self.mqtt_password)

            if self.mqtt_use_tls:
                self._mqtt.tls_set()

            logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port} TLS={self.mqtt_use_tls}")
            self._mqtt.connect(self.mqtt_broker, self.mqtt_port, 60)
            self._mqtt.loop_start()

            timeout = 10
            start = time.time()
            while not self._connected and time.time() - start < timeout:
                time.sleep(0.1)

            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("Successfully connected to MQTT")
            client.subscribe(self.control_topic)
            logger.info(f"Subscribed to: {self.control_topic}")

            # Debug subscription: helps detect if bot publishes to a different device_id
            client.subscribe("iot/devices/+/control")
            logger.info("Subscribed to: iot/devices/+/control")

            self.refresh_state_and_publish()
        else:
            logger.error(f"Failed to connect to MQTT, rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"Disconnected from MQTT (rc={rc})")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"Message received on {msg.topic}: {payload}")
            command = json.loads(payload)
        except Exception as e:
            logger.error(f"Invalid command payload: {e}")
            return

        # If wildcard subscription receives commands for other devices, just log and ignore
        if msg.topic != self.control_topic:
            return

        try:
            with self._lock:
                self._apply_command(command)

            self.refresh_state_and_publish()
        except Exception as e:
            logger.error(f"Failed to apply command: {e}")
            self.publish_status(online=False, extra={"error": str(e)})

    def _apply_command(self, command: Dict[str, Any]):
        action = command.get("action")

        # If datapoints haven't been inferred yet, do a quick status() now.
        if self._dp_power is None and self._dp_brightness is None and self._dp_color is None:
            try:
                state = self._tuya.status()
                self._infer_datapoints_from_state(state)
            except Exception:
                pass

        if action == "power":
            state = bool(command.get("state", False))
            if self._dp_power is not None:
                self._tuya.set_status(state, self._dp_power)
            else:
                # Fallback to library defaults
                if state:
                    self._tuya.turn_on()
                else:
                    self._tuya.turn_off()

        elif action == "brightness":
            value = int(command.get("value", 100))
            value = max(0, min(100, value))
            if self._dp_brightness is not None:
                # Common Tuya scale is 10-1000
                scaled = int(max(10, min(1000, round((value / 100.0) * 1000))))
                self._tuya.set_value(self._dp_brightness, scaled)
            else:
                self._tuya.set_brightness_percentage(value)

        elif action == "color":
            r = int(command.get("red", 255))
            g = int(command.get("green", 255))
            b = int(command.get("blue", 255))
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            # Some devices require a mode switch before color works; tinytuya handles most cases.
            self._tuya.set_colour(r, g, b)

        elif action == "preset":
            name = str(command.get("name", "")).lower()
            presets = {
                "warm": (255, 200, 100),
                "cool": (200, 200, 255),
                "romantic": (255, 100, 150),
                "party": (255, 0, 255),
                "reading": (255, 255, 200),
                "sunset": (255, 150, 50),
                "ocean": (0, 150, 255),
                "forest": (50, 255, 50),
                "night": (255, 180, 80),
                "day": (255, 255, 255),
            }
            if name not in presets:
                raise ValueError(f"Unknown preset: {name}")

            r, g, b = presets[name]
            self._tuya.set_colour(r, g, b)

        else:
            raise ValueError(f"Unknown action: {action}")

    def refresh_state_and_publish(self):
        try:
            logger.info("Refreshing Tuya state (status())...")
            state = self._tuya.status()
            logger.info("Tuya state received")
            dps = (state or {}).get("dps") or {}
            if not isinstance(dps, dict) or len(dps) == 0:
                # When auth/protocol is wrong, tinytuya can sometimes return empty DPS or an error field.
                err = None
                if isinstance(state, dict):
                    err = state.get("Error") or state.get("error")

                state_keys = list(state.keys()) if isinstance(state, dict) else []
                logger.warning(f"Tuya status has empty DPS. keys={state_keys} error={err}")
                logger.info(f"Tuya raw state: {state}")
                self.publish_status(online=False, extra={"error": "empty_dps"})
                return

            self._infer_datapoints_from_state(state)
            self._update_cached_state_from_tuya(state)
            self.publish_status(online=True)
        except Exception as e:
            logger.error(f"Failed to refresh Tuya state: {e}")
            self.publish_status(online=False, extra={"error": str(e)})

    def _infer_datapoints_from_state(self, state: Dict[str, Any]):
        dps = state.get("dps") or {}

        # Log DPS once we see them (helps mapping)
        logger.info(f"Tuya DPS: {dps}")

        # Infer power datapoint: many bulbs use 20, some use 1
        if self._dp_power is None:
            for cand in (20, 1):
                if str(cand) in dps or cand in dps:
                    val = dps.get(str(cand), dps.get(cand))
                    if isinstance(val, bool):
                        self._dp_power = cand
                        break

        # Infer brightness datapoint: common 22, sometimes 2/3
        if self._dp_brightness is None:
            for cand in (22, 2, 3):
                if str(cand) in dps or cand in dps:
                    val = dps.get(str(cand), dps.get(cand))
                    if isinstance(val, (int, float)):
                        self._dp_brightness = cand
                        break

        # Infer color datapoint: common 24 (string)
        if self._dp_color is None:
            for cand in (24, 5):
                if str(cand) in dps or cand in dps:
                    val = dps.get(str(cand), dps.get(cand))
                    if isinstance(val, str):
                        self._dp_color = cand
                        break

    def _update_cached_state_from_tuya(self, state: Dict[str, Any]):
        dps = state.get("dps") or {}

        # Use inferred datapoints first
        if self._dp_power is not None:
            power = dps.get(str(self._dp_power), dps.get(self._dp_power))
            if isinstance(power, bool):
                self._power_on = power

        if self._dp_brightness is not None:
            bright = dps.get(str(self._dp_brightness), dps.get(self._dp_brightness))
            if isinstance(bright, (int, float)):
                # Many Tuya bulbs use 10-1000 scale, but some use 0-100.
                # We normalize to 0-100 for MQTT.
                if bright > 100:
                    self._brightness = int(max(0, min(100, round((float(bright) / 1000.0) * 100))))
                else:
                    self._brightness = int(max(0, min(100, round(float(bright)))))

        # If device reports colour via DPS 24 (hex), tinytuya can decode it but format differs per device.
        # We keep last known RGB if parsing is not possible.

    def publish_status(self, online: bool, extra: Optional[Dict[str, Any]] = None):
        payload: Dict[str, Any] = {
            "device_id": self.device_id,
            "type": "smart_bulb",
            "online": bool(online),
            "power": self._power_on,
            "red": self._red,
            "green": self._green,
            "blue": self._blue,
            "brightness": self._brightness,
            "timestamp": datetime.now().isoformat(),
        }

        if extra:
            payload.update(extra)

        try:
            self._mqtt.publish(self.status_topic, json.dumps(payload))
            logger.info(
                f"📡 Status sent: online={online}, power={self._power_on}, brightness={self._brightness}"
            )
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")

    def run(self):
        logger.info("🌟 Tuya Bulb Bridge starting...")
        logger.info(f"📱 MQTT device_id: {self.device_id}")
        logger.info(f"🏠 Tuya host: {self.tuya_host} (v{self.tuya_version})")

        if not self.connect():
            logger.error("Failed to connect to MQTT broker")
            return

        try:
            while True:
                time.sleep(30)
                self.refresh_state_and_publish()
        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user")
        finally:
            try:
                self._mqtt.loop_stop()
                self._mqtt.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    TuyaBulbBridge().run()
