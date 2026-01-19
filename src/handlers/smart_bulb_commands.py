"""
Smart Bulb Commands Module
Controls RGB smart bulbs via MQTT
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from src.mqtt.client import SimpleMQTTClient

logger = logging.getLogger(__name__)

class SmartBulbCommands:
    def __init__(self, mqtt_client: SimpleMQTTClient):
        self.mqtt_client = mqtt_client
        self.bulb_device_id = "smart_bulb_01"
        
        # Color presets
        self.presets = {
            "warm": {"red": 255, "green": 200, "blue": 100},
            "cool": {"red": 200, "green": 200, "blue": 255},
            "romantic": {"red": 255, "green": 100, "blue": 150},
            "party": {"red": 255, "green": 0, "blue": 255},
            "reading": {"red": 255, "green": 255, "blue": 200},
            "sunset": {"red": 255, "green": 150, "blue": 50},
            "ocean": {"red": 0, "green": 150, "blue": 255},
            "forest": {"red": 50, "green": 255, "blue": 50}
        }
    
    async def show_bulb_control(self, query, device_id: str = None):
        """Show smart bulb control panel"""
        try:
            bulb_id = device_id or self.bulb_device_id
            
            # Get current bulb status
            device_data = self.mqtt_client.get_device_data(bulb_id)
            
            if not device_data:
                await self._send_bulb_message(query, f"❌ Smart bulb '{bulb_id}' not found or offline.")
                return
            
            status = device_data.get('status', {})
            power_on = status.get('power', False)
            red = status.get('red', 255)
            green = status.get('green', 255)
            blue = status.get('blue', 255)
            
            # Create control panel
            power_text = "🟢 ON" if power_on else "🔴 OFF"
            color_hex = self._rgb_to_hex(red, green, blue)
            
            text = f"💡 **Smart Bulb Control**\n\n"
            text += f"📱 Device: `{bulb_id}`\n"
            text += f"🔌 Power: {power_text}\n"
            text += f"🎨 Color: {color_hex} (R:{red}, G:{green}, B:{blue})\n\n"
            text += f"💬 *Choose control option:*"
            
            # Control buttons - bulb specific
            keyboard = [
                [
                    InlineKeyboardButton(f"🔌 {'Išjungti' if power_on else 'Įjungti'}", 
                                       callback_data=f'bulb|power|{bulb_id}|{not power_on}'),
                    InlineKeyboardButton("🎨 Spalvos", callback_data=f'bulb|color|{bulb_id}')
                ],
                [
                    InlineKeyboardButton("🔆 Šviesumas", callback_data=f'bulb|brightness|{bulb_id}|control'),
                    InlineKeyboardButton("✨ Efektai", callback_data=f'bulb|presets|{bulb_id}')
                ],
                [
                    InlineKeyboardButton("🌙 Naktis", callback_data=f'bulb|night|{bulb_id}'),
                    InlineKeyboardButton("☀️ Diena", callback_data=f'bulb|day|{bulb_id}')
                ],
                [
                    InlineKeyboardButton("🔄 Atnaujinti", callback_data=f'bulb|refresh|{bulb_id}'),
                    InlineKeyboardButton("⬅️ Atgal", callback_data='devices_list')
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                if hasattr(query, 'edit_message_text'):
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            except BadRequest as e:
                if "message is not modified" in str(e).lower():
                    pass  # Ignore - same content
                else:
                    raise
                
        except Exception as e:
            logger.error(f"Error showing bulb control: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    async def toggle_power(self, query, bulb_id: str, state: bool):
        """Toggle bulb power"""
        try:
            logger.info(f"toggle_power called: bulb_id={bulb_id}, state={state}")
            command_data = {
                "action": "power",
                "state": state
            }
            
            logger.info(f"Publishing command to {bulb_id}: {command_data}")
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            logger.info(f"Command published successfully")
            
            action_text = "turned ON" if state else "turned OFF"
            await self._send_bulb_message(query, f"💡 Bulb {action_text}!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error toggling bulb power: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    async def show_color_picker(self, query, bulb_id: str):
        """Show color selection panel"""
        try:
            text = f"🎨 **Spalvų pasirinkimas**\n\n"
            text += f"💡 Pasirinkite spalvą lemputei `{bulb_id}`:\n\n"
            text += f"🌈 *Pagrindinės spalvos:*"
            
            # Color buttons - 4x4 grid
            colors = [
                ("🔴 Raudona", 255, 0, 0), ("🟠 Oranžinė", 255, 165, 0), ("🟡 Geltona", 255, 255, 0), ("🟢 Žalia", 0, 255, 0),
                ("🔵 Mėlyna", 0, 0, 255), ("🟣 Violetinė", 128, 0, 128), ("⚪ Balta", 255, 255, 255), ("⚫ Juoda", 0, 0, 0),
                ("🌸 Rožinė", 255, 192, 203), ("🌊 Žydra", 0, 191, 255), ("🌿 Šviesiai žalia", 144, 238, 144), ("🔥 Ugnies", 255, 69, 0),
                ("� Purpurinė", 138, 43, 226), ("💙 Tamsiai mėlyna", 70, 130, 180), ("💚 Tamsiai žalia", 34, 139, 34), ("❤️ Ryškiai raudona", 220, 20, 60)
            ]
            
            keyboard = []
            for i in range(0, len(colors), 4):
                row = []
                for j in range(4):
                    if i + j < len(colors):
                        name, r, g, b = colors[i + j]
                        emoji = name.split()[0]
                        row.append(InlineKeyboardButton(
                            emoji, 
                            callback_data=f'bulb|setcolor|{bulb_id}|{r}|{g}|{b}'
                        ))
                keyboard.append(row)
            
            # Add warm/cool white options and back button
            keyboard.extend([
                [
                    InlineKeyboardButton("🌅 Šiltai balta", callback_data=f'bulb|setcolor|{bulb_id}|255|244|229'),
                    InlineKeyboardButton("❄️ Šaltai balta", callback_data=f'bulb|setcolor|{bulb_id}|229|244|255')
                ],
                [
                    InlineKeyboardButton("⬅️ Atgal", callback_data=f'bulb|control|{bulb_id}')
                ]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error showing color picker: {e}")
            await self._send_bulb_message(query, f"❌ Klaida: {str(e)}")
    
    async def set_color(self, query, bulb_id: str, red: int, green: int, blue: int):
        """Set bulb color"""
        try:
            command_data = {
                "action": "color",
                "red": red,
                "green": green,
                "blue": blue
            }
            
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            
            color_hex = self._rgb_to_hex(red, green, blue)
            await self._send_bulb_message(query, f"🎨 Color set to {color_hex}!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error setting bulb color: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    async def show_brightness_control(self, query, bulb_id: str):
        """Show brightness control panel"""
        try:
            text = f"🔆 **Šviesumo valdymas**\n\n"
            text += f"💡 Reguliuokite šviesumą lemputei `{bulb_id}`:\n\n"
            text += f"☀️ *Pasirinkite šviesumo lygį:*"
            
            # Brightness buttons (10% increments)
            keyboard = []
            brightness_levels = [
                (10, "🌙 Naktinis"), (25, "🌑 Labai tamsu"), 
                (50, "🌗 Pusei"), (75, "🌔 Šviesiai"), (100, "☀️ Maksimalus")
            ]
            
            for brightness, name in brightness_levels:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{name} ({brightness}%)", 
                        callback_data=f'bulb|brightness|{bulb_id}|{brightness}'
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("⬅️ Atgal", callback_data=f'bulb|control|{bulb_id}')
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error showing brightness control: {e}")
            await self._send_bulb_message(query, f"❌ Klaida: {str(e)}")
    
    async def set_night_mode(self, query, bulb_id: str):
        """Set night mode - warm, low brightness"""
        try:
            command_data = {
                "action": "preset",
                "name": "night"
            }
            
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            await self._send_bulb_message(query, f"🌙 Naktinis režimas įjungtas!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error setting night mode: {e}")
            await self._send_bulb_message(query, f"❌ Klaida: {str(e)}")
    
    async def set_day_mode(self, query, bulb_id: str):
        """Set day mode - bright white"""
        try:
            command_data = {
                "action": "preset", 
                "name": "day"
            }
            
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            await self._send_bulb_message(query, f"☀️ Dienos režimas įjungtas!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error setting day mode: {e}")
            await self._send_bulb_message(query, f"❌ Klaida: {str(e)}")
    
    async def set_brightness(self, query, bulb_id: str, brightness: int):
        """Set bulb brightness"""
        try:
            command_data = {
                "action": "brightness",
                "value": brightness
            }
            
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            
            emoji = "🌑" if brightness <= 25 else "🌗" if brightness <= 50 else "🌔" if brightness <= 75 else "☀️"
            await self._send_bulb_message(query, f"{emoji} Brightness set to {brightness}!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    async def show_presets(self, query, bulb_id: str):
        """Show color presets"""
        try:
            text = f"✨ **Color Presets**\n\n"
            text += f"💡 Quick color themes for `{bulb_id}`:\n\n"
            text += f"🎭 *Choose a preset:*"
            
            keyboard = []

            # Preset buttons
            for preset_name in self.presets.keys():
                emoji = self._get_preset_emoji(preset_name)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {preset_name.title()}",
                        callback_data=f'bulb|preset|{bulb_id}|{preset_name}'
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("⬅️ Atgal", callback_data=f'bulb|control|{bulb_id}')
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error showing presets: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    async def apply_preset(self, query, bulb_id: str, preset_name: str):
        """Apply color preset"""
        try:
            if preset_name not in self.presets:
                await self._send_bulb_message(query, f"❌ Preset '{preset_name}' not found.")
                return
            
            color = self.presets[preset_name]
            command_data = {
                "action": "preset",
                "name": preset_name
            }
            
            self.mqtt_client.publish_device_command(bulb_id, command_data)
            
            emoji = self._get_preset_emoji(preset_name)
            await self._send_bulb_message(query, f"{emoji} Applied {preset_name.title()} preset!", show_controls=True, device_id=bulb_id)
            
        except Exception as e:
            logger.error(f"Error applying preset: {e}")
            await self._send_bulb_message(query, f"❌ Error: {str(e)}")
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB to hex color"""
        return f"#{r:02X}{g:02X}{b:02X}"
    
    def _get_preset_emoji(self, preset_name: str) -> str:
        """Get emoji for preset"""
        emoji_map = {
            "warm": "🌅",
            "cool": "❄️", 
            "romantic": "💕",
            "party": "🎉",
            "reading": "📖",
            "sunset": "🌇",
            "ocean": "🌊",
            "forest": "🌲"
        }
        return emoji_map.get(preset_name, "✨")
    
    async def _send_bulb_message(self, query, message: str, show_controls: bool = False, device_id: str = None):
        """Send message and optionally show controls"""
        try:
            if show_controls and device_id:
                # Show controls after action
                await self.show_bulb_control(query, device_id)
            else:
                # Just send message
                if hasattr(query, 'edit_message_text'):
                    await query.edit_message_text(message)
                elif hasattr(query, 'reply_text'):
                    await query.reply_text(message)
                elif hasattr(query, 'message') and hasattr(query.message, 'reply_text'):
                    await query.message.reply_text(message)
                else:
                    # Fallback - try to send as new message
                    logger.warning(f"Cannot send message to query type: {type(query)}")
        except Exception as e:
            logger.error(f"Error sending bulb message: {e}")
