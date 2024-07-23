import asyncpg
from asyncpg.pool import Pool
import os
from dotenv import load_dotenv

load_dotenv()


# PostgreSQL connection details
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")

class PostgresSessionStorage:
    def __init__(self):
        self.pool: Pool = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE
        )
        
        # Create the sessions table if it doesn't exist
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    channel_id BIGINT PRIMARY KEY,
                    session_id UUID NOT NULL
                )
            ''')

    async def get_session_id(self, channel_id: int) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT session_id FROM sessions WHERE channel_id = $1',
                channel_id
            )
            if row:
                return str(row['session_id'])
            
            # If no session exists, create a new one
            session_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO sessions (channel_id, session_id) VALUES ($1, $2)',
                channel_id, session_id
            )
            return session_id

    async def close(self):
        await self.pool.close()

# Modify the bot initialization to use PostgresSessionStorage
session_storage = PostgresSessionStorage()

@bot.event
async def on_ready():
    await session_storage.initialize()
    print(f'{bot.user} has connected to Discord!')

# Modify the existing get_channel_session_id function
async def get_channel_session_id(channel_id):
    return await session_storage.get_session_id(channel_id)

# Modify the on_message event to use the async version
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = message.channel.id
    content = message.content
    session_id = await get_channel_session_id(channel_id)

    # ... rest of the on_message logic ...

# Make sure to close the database connection when the bot shuts down
@bot.event
async def on_shutdown():
    await session_storage.close()

# Don't forget to add this to your bot.run() call
bot.run(os.getenv("DISCORD_BOT_TOKEN"), on_shutdown=on_shutdown)
