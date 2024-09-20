import asyncio
from zep_integration import ZepIntegration
from discord_bot import DiscordBot
from telegram_bot import TelegramBot
from config import *

async def main():
    # Initialize Zep integration
    zep_integration = ZepIntegration(ZEP_API_URL, ZEP_API_KEY, PG_CONFIG)
    await zep_integration.initialize()

    # Initialize Discord bot
    discord_bot = DiscordBot(zep_integration, OPENAI_API_KEY, DISCORD_BOT_TOKEN)
    
    # Initialize Telegram bot
    telegram_bot = TelegramBot(zep_integration, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN)

    # Start both bots concurrently
    await asyncio.gather(
        discord_bot.start(),
        telegram_bot.start()
    )

if __name__ == "__main__":
    asyncio.run(main())