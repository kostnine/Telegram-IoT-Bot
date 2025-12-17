#!/usr/bin/env python3
"""
Telegram IoT Bot - Entry Point
Run this file to start the bot
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot.main import TelegramIoTBot

async def main():
    """Main function"""
    bot = TelegramIoTBot()
    await bot.run()

if __name__ == "__main__":
    # Fix for Windows compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
