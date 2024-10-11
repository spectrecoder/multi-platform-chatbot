import os
import logging
import asyncio
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Union
import numpy as np

from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from environment variables
ZEP_API_URL = os.getenv("ZEP_API_URL")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_COMMAND_PREFIX = os.getenv('BOT_PREFIX')

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")

# Initialize clients
openai.api_key = OPENAI_API_KEY
zep_client = ZepClient(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)

# Configuration parameters
MAX_MESSAGES_BEFORE_SUMMARY = 75
MAX_CHARS_BEFORE_SUMMARY = 12000
SUMMARY_WORD_LIMIT = 200
SUMMARY_MAX_AGE_HOURS = 24
MAX_TOKENS_FOR_SUMMARY = 3000
RELEVANCE_THRESHOLD = 0.5
MAX_CONTEXT_TOKENS = 3000
SUMMARIZATION_MODEL = "gpt-4o-mini"
RESPONSE_GENERATION_MODEL = "gpt-4o-mini"
SEARCH_RESULT_LIMIT = 100

class PostgresSessionStorage:
    def __init__(self):
        self.pool: Pool = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, user=PG_USER,
            password=PG_PASSWORD, database=PG_DATABASE
        )
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    chat_id TEXT PRIMARY KEY,
                    session_id UUID NOT NULL
                )
            ''')

    async def get_session_id(self, chat_id: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT session_id FROM sessions WHERE chat_id = $1',
                chat_id
            )
            if row:
                return str(row['session_id'])
            
            session_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO sessions (chat_id, session_id) VALUES ($1, $2)',
                chat_id, session_id
            )
            return session_id

    async def close(self):
        await self.pool.close()

session_storage = PostgresSessionStorage()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix=BOT_COMMAND_PREFIX, intents=intents, help_command=None)

# Telegram bot setup
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def get_session_id(chat_id: Union[int, str]) -> str:
    return await session_storage.get_session_id(str(chat_id))

async def save_message(session_id: str, role: str, content: str, timestamp: datetime):
    memory = Memory(
        messages=[Message(role=role, content=content, timestamp=timestamp)],
        metadata={"session_id": session_id}
    )
    zep_client.memory.add_memory(session_id, memory)

async def generate_response(session_id: str, user_message: str) -> str:
    messages = await zep_client.message.aget_session_messages(session_id)
    chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])

    gpt_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Chat history:\n{chat_history}\n\nUser: {user_message}"}
    ]

    response = await openai.ChatCompletion.acreate(
        model=RESPONSE_GENERATION_MODEL,
        messages=gpt_messages
    )

    return response.choices[0].message.content.strip()

async def search_chat(session_id: str, keyword: str) -> List[str]:
    search_payload = MemorySearchPayload(
        text=keyword,
        search_scope="messages",
        search_type="mmr",
        mmr_lambda=0.5
    )

    search_results = await zep_client.memory.asearch_memory(session_id, search_payload, limit=5)
    
    results = []
    for result in search_results:
        if result.message:
            content = result.message.get('content', 'No content available')
            highlighted_content = re.sub(
                f'({re.escape(keyword)})',
                lambda m: f"<<{m.group(1).upper()}>>",
                content,
                flags=re.IGNORECASE
            )
            results.append(highlighted_content)

    return results

# Discord event handlers
@discord_bot.event
async def on_ready():
    await session_storage.initialize()
    print(f'{discord_bot.user} has connected to Discord!')

@discord_bot.event
async def on_message(message):
    if message.author == discord_bot.user:
        return

    session_id = await get_session_id(str(message.channel.id))
    content = message.content
    timestamp = message.created_at

    await save_message(session_id, "user", f"{message.author.name}: {content}", timestamp)

    if discord_bot.user.mentioned_in(message) or message.content.lower().startswith('bot,'):
        clean_content = message.content.replace(f'<@{discord_bot.user.id}>', '').strip()
        clean_content = clean_content[4:] if clean_content.lower().startswith('bot,') else clean_content

        thinking_message = await message.channel.send("Thinking...")
        
        response = await generate_response(session_id, clean_content)
        
        await thinking_message.edit(content=response)
        await save_message(session_id, "assistant", response, datetime.utcnow())

    await discord_bot.process_commands(message)

@discord_bot.command(name='search')
async def discord_search(ctx, keyword: str):
    session_id = await get_session_id(str(ctx.channel.id))
    results = await search_chat(session_id, keyword)
    
    if results:
        response = "Search results:\n\n" + "\n\n".join(results)
    else:
        response = "No results found for the given keyword."

    await ctx.send(response)

# Telegram event handlers
async def telegram_start(update: Update, context):
    await update.message.reply_text('Hello! I am your AI assistant. Mention me to ask questions. Use /search <keyword> to search chat logs.')

async def telegram_handle_message(update: Update, context):
    message = update.message
    chat_id = str(message.chat_id)
    user_id = str(message.from_user.id)
    text = message.text
    timestamp = message.date

    session_id = await get_session_id(chat_id)
    await save_message(session_id, "user", f"{user_id} ({timestamp}): {text}", timestamp)

    if context.bot.username in text:
        thinking_message = await update.message.reply_text("Thinking...")
        
        response = await generate_response(session_id, text)
        
        await thinking_message.edit_text(response)
        await save_message(session_id, "assistant", f"({datetime.utcnow()}): {response}", datetime.utcnow())

async def telegram_search_chat(update: Update, context):
    if not context.args:
        await update.message.reply_text("Please provide a search keyword. Usage: /search <keyword>")
        return

    keyword = " ".join(context.args)
    chat_id = str(update.message.chat_id)
    session_id = await get_session_id(chat_id)

    search_message = await update.message.reply_text("Searching...")
    results = await search_chat(session_id, keyword)
    
    if results:
        response = "Search results:\n\n" + "\n\n".join(results)
    else:
        response = "No results found for the given keyword."

    await search_message.edit_text(response)

async def error_handler(update: Update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# Main function to run both bots
def main():
    # Set up and run Discord bot
    discord_bot.run(DISCORD_BOT_TOKEN)

    # Set up and run Telegram bot
    telegram_app.add_handler(CommandHandler("start", telegram_start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handle_message))
    telegram_app.add_handler(CommandHandler("search", telegram_search_chat))
    telegram_app.add_error_handler(error_handler)
    telegram_app.run_polling()

if __name__ == '__main__':
    main()