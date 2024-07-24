import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from asyncio import TimeoutError
import re
import io
import requests
import uuid
from datetime import datetime, timedelta
import json
import numpy as np
import asyncpg
from asyncpg.pool import Pool

from zep_python import (ZepClient, MemorySearchPayload)
from zep_python.memory import Memory, Message


load_dotenv()


PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")







BOT_COMMAND_PREFIX = os.getenv('BOT_PREFIX')
ZEP_API_URL = os.getenv("ZEP_API_URL")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")


recent_prompts = []

message_counters = {}



zep_client = ZepClient(ZEP_API_URL, ZEP_API_KEY)



  # Prefix for bot commands


GREETING_PHRASES = [
    "hello", "hi", "hey", "howdy", "greetings", "good morning", "good afternoon", 
    "good evening", "what's up", "sup", "yo", "hiya"
]

# Compile a regex pattern for efficient matching
GREETING_PATTERN = re.compile(r'\b(' + '|'.join(GREETING_PHRASES) + r')\b', re.IGNORECASE)

# Bot Setup


# Configuration Parameters
# ------------------------

# Memory and Summarization
MAX_MESSAGES_BEFORE_SUMMARY = 75  # Number of messages before triggering a summary
MAX_CHARS_BEFORE_SUMMARY = 12000  # Total character count before triggering a summary
SUMMARY_WORD_LIMIT = 200  # Maximum word count for generated summaries
SUMMARY_MAX_AGE_HOURS = 24  # Maximum age of a summary before it's updated, regardless of message count

# Context Retrieval
RELEVANCE_THRESHOLD = 0.5  # Minimum relevance score for including messages/summaries
INITIAL_SUMMARY_PERCENTAGE = 0.9  # Starting percentage of messages to include from each summary
SUMMARY_PERCENTAGE_REDUCTION = 0.1  # Reduction in percentage for each successive summary
MIN_SUMMARY_PERCENTAGE = 0.5  # Minimum percentage of messages to include from a summary
MAX_CONTEXT_TOKENS = 3000  # Maximum number of tokens for the entire context
SUMMARY_CONTEXT_PERCENTAGE = 0.7  # Percentage of context dedicated to summary-related messages

# Model Selection
SUMMARIZATION_MODEL = "gpt-4o-mini"  # Model to use for generating summaries
RESPONSE_GENERATION_MODEL = "gpt-4o-mini"  # Model to use for generating bot responses
EMBEDDING_MODEL = "text-embedding-ada-002"  # Model to use for creating embeddings

# Search and Ranking
SEARCH_RESULT_LIMIT = 100  # Maximum number of results to retrieve from memory search
MMR_LAMBDA = 0.5  # Lambda parameter for MMR reranking

# Discord Bot Settings


# Summarization Process
SUMMARY_STYLE = "concise"  # Options: "concise", "detailed", "bullet-points"
SUMMARY_FOCUS = "key_points"  # Options: "key_points", "chronological", "topic_based"
SUMMARY_SENTIMENT = False  # Include sentiment analysis in summaries
SUMMARY_ENTITIES = True  # Highlight key entities or names in summaries

# Bot Response Customization
RESPONSE_LENGTH = "medium"  # Options: "short", "medium", "long"
RESPONSE_STYLE = "casual"  # Options: "formal", "casual", "humorous"
RESPONSE_COMPLEXITY = "moderate"  # Options: "simple", "moderate", "advanced"
RESPONSE_FORMATTING = True  # Enable use of markdown, bullet points, etc.
RESPONSE_CITATIONS = False  # Include citations or references to source messages

# Similarity Metrics
SIMILARITY_METRIC = "cosine"  # Options: "cosine", "euclidean", "jaccard", "levenshtein"
VECTOR_NORMALIZATION = True  # Enable normalization of vectors before similarity calculation
SIMILARITY_WEIGHTING = None  # Apply custom weighting to different parts of the embedding
CONTEXTUAL_SIMILARITY = False  # Consider surrounding messages when calculating similarity

# Rate Limiting and Cooldown
RATE_LIMIT_MESSAGES = 30  # Maximum number of messages per user per minute
RATE_LIMIT_COMMANDS = 20  # Maximum number of commands per user per hour
COOLDOWN_DURATION = 5  # Seconds a user must wait between using specific commands
BURST_ALLOWANCE = 5  # Number of rapid requests allowed before rate limiting kicks in
RATE_LIMIT_RESPONSE = "You're doing that too much. Please wait a moment and try again."

# Context Retention
CONTEXT_RETENTION_MESSAGES = 10  # Number of previous messages to retain for context
CONTEXT_RETENTION_TIME = 30  # Minutes to retain context
CONTEXT_RELEVANCE_DECAY = 0.9  # Factor by which to reduce relevance of older context
TOPIC_CHANGE_THRESHOLD = 0.3  # Sensitivity for detecting a change in conversation topic
MULTI_TURN_MAX_TURNS = 5  # Maximum number of turns to consider in a single conversation

# Error Handling and Fallback
ERROR_RETRY_ATTEMPTS = 3  # Number of times to retry failed API calls
FALLBACK_RESPONSE = "I'm having trouble processing that right now. Could you try rephrasing your request?"
ERROR_LOGGING_LEVEL = "detailed"  # Options: "minimal", "detailed"

# Performance Optimization
CACHE_DURATION = 3600  # Seconds to cache embeddings or frequent queries
BATCH_SIZE = 10  # Number of items to process in a single batch for efficiency
ASYNC_PROCESSING = True  # Enable asynchronous processing of non-critical tasks

# Integration with External Services
ENABLE_WEATHER_API = False  # Toggle integration with weather service
ENABLE_NEWS_API = False  # Toggle integration with news service
API_TIMEOUT = 5  # Maximum wait time for external API responses in seconds

# API Keys and Credentials

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_COMMAND_PREFIX, intents=intents, help_command=None)


def highlight_keyword(text, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(f"*`{keyword}`*", text)


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

session_storage = PostgresSessionStorage()

@bot.event
async def on_ready():
    await session_storage.initialize()
    print(f'{bot.user} has connected to Discord!')

async def get_channel_session_id(channel_id):
    return await session_storage.get_session_id(channel_id)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = message.channel.id
    content = message.content
    session_id = await get_channel_session_id(channel_id)

    # Check if the message is a command starting with '/'
    is_slash_command = content.startswith('/')

    # Check if the message is a greeting
    is_greeting = bool(GREETING_PATTERN.search(content))

    try:
        memory = Memory(
            messages=[Message(role="user", content=f"{message.author.name}: {content}")],
            metadata={"session_id": session_id}
        )
        zep_client.memory.add_memory(session_id, memory)
        print(f"Message saved: {content}")

        # Increment the message counter for this session
        if session_id not in message_counters:
            message_counters[session_id] = 0
        message_counters[session_id] += 1


        # Check if we need to create a summary, but not for slash commands or greetings
        if not is_slash_command and not is_greeting and message_counters[session_id]>=10:
            await check_and_summarize(session_id)
            message_counters[session_id] = 0
            
    except Exception as e:
        print(f"Error saving message or summarizing: {e}")

    if bot.user.mentioned_in(message) or message.content.lower().startswith('bot,'):
        clean_content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        clean_content = clean_content[4:] if clean_content.lower().startswith('bot,') else clean_content

        thinking_message = await message.channel.send("Thinking...")

        async with message.channel.typing():
            response = await generate_response(channel_id, clean_content)

            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]

            await thinking_message.edit(content=chunks[0])

            for chunk in chunks[1:]:
                await message.channel.send(chunk)

        try:
            memory = Memory(
                messages=[Message(role="assistant", content=response)],
                metadata={"session_id": session_id}
            )
            zep_client.memory.add_memory(session_id, memory)
            print(f"Bot response saved: {response}")
        except Exception as e:
            print(f"Error saving bot response: {e}")

    # This line is crucial for processing commands
    await bot.process_commands(message)


async def generate_response(channel_id, user_message):
    session_id = get_channel_session_id(channel_id)

    async with ZepClient(ZEP_API_URL, ZEP_API_KEY) as client:
        try:
            historical_messages = await zep_client.message.aget_session_messages(
                session_id)
            print(len(historical_messages))
        except Exception as e:
            print(f"Error retrieving historical messages: {e}")
            historical_messages = []

    system_message = {
        "role":
        "system",
        "content":
        "You are a helpful assistant in a Discord server. Use the provided conversation history to give informed and coherent responses."
    }

    messages = [system_message]
    user_chat_logs = []

    for memory in historical_messages:
        messages.append({"role": memory.role, "content": memory.content})
        if memory.role == "user":
            content = extract_message_content(memory.content)
            if is_valid_message(content):
                user_chat_logs.append(content)

    current_user_message = {"role": "user", "content": user_message}
    messages.append(current_user_message)

    full_prompt = " ".join(user_chat_logs)

    try:
        response = openai.ChatCompletion.create(model="gpt-4o-mini",
                                                messages=messages)
        ai_response = response.choices[0].message['content']

        recent_prompts.append({
            "question": user_message,
            "prompt_summary": full_prompt
        })
        if len(recent_prompts) > 5:
            recent_prompts.pop(0)

        if len(ai_response) > 2000:
            summarize_messages = [{
                "role":
                "system",
                "content":
                "You are a summarizer. Summarize the following text in less than 1500 characters while retaining the most important information."
            }, {
                "role": "user",
                "content": ai_response
            }]
            summary_response = openai.ChatCompletion.create(
                model="gpt-4o-mini", messages=summarize_messages)
            ai_response = summary_response.choices[0].message['content']

        memory = Memory(
            messages=[Message(role="assistant", content=ai_response)])
        zep_client.memory.add_memory(session_id, memory)

        return ai_response
    except Exception as e:
        return f"An error occurred: {str(e)}"




async def check_and_summarize(session_id):
    messages = await zep_client.message.aget_session_messages(session_id)
    
    if not messages:
        print(f"No messages found for session {session_id}")
        return
    
    last_summary = await get_last_summary(session_id)

    if last_summary == "This is your first message in this channel":
        # If there's no previous summary, treat all messages as new
        messages_since_last_summary = messages
        summary_age = timedelta(hours=SUMMARY_MAX_AGE_HOURS + 1)
    else:
        messages_since_last_summary = [m for m in messages if m.created_at > last_summary.created_at]
        current_time = datetime.now()
        summary_age = current_time - last_summary.created_at

    if not messages_since_last_summary:
        print(f"No new messages since last summary for session {session_id}")
        return

    if (len(messages_since_last_summary) >= MAX_MESSAGES_BEFORE_SUMMARY or
        sum(len(m.content) for m in messages_since_last_summary) >= MAX_CHARS_BEFORE_SUMMARY or
        summary_age.total_seconds() / 3600 >= SUMMARY_MAX_AGE_HOURS):
        await create_summary(session_id, messages_since_last_summary)



async def get_last_summary(session_id):
    try:
        searchPayload = MemorySearchPayload(
            search_scope="summary",
            text="latest summary"  # Add a non-empty search text
        )
        summaries = await zep_client.memory.search_memory(session_id, searchPayload, limit=1)
        return summaries[0] if summaries else "hi"
    except Exception as e:
        # print(f"Error getting last summary for session {session_id}: {str(e)}")
        return "This is your first message in this channel"


async def create_summary(session_id, messages):
    if not messages:
        print(f"No messages to summarize for session {session_id}")
        return

    combined_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

    if not combined_text.strip():
        print(f"Empty combined text for session {session_id}")
        return

    summary_prompt = f"Summarize the following conversation in {SUMMARY_WORD_LIMIT} words or less. "
    summary_prompt += f"Style: {SUMMARY_STYLE}. Focus: {SUMMARY_FOCUS}. "
    if SUMMARY_SENTIMENT:
        summary_prompt += "Include overall sentiment. "
    if SUMMARY_ENTITIES:
        summary_prompt += "Highlight key entities or names. "
    summary_prompt += "Conversation:\n" + combined_text

    try:
        response = openai.ChatCompletion.create(
            model=SUMMARIZATION_MODEL,
            messages=[
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = response.choices[0].message['content']

        summary_memory = Memory(
            messages=[Message(role="system", content=f"Summary: {summary}")],
            metadata={"type": "summary", "start_time": messages[0].created_at, "end_time": messages[-1].created_at}
        )
        # Use the synchronous version of add_memory
        zep_client.memory.add_memory(session_id, summary_memory)
        print(f"Summary created and added for session {session_id}")
    except Exception as e:
        print(f"Error creating summary for session {session_id}: {str(e)}")



async def get_relevant_context(session_id, query, max_tokens):
    searchPayload = MemorySearchPayload(
        text=query,
        search_scope="summary"
    )
    results = await zep_client.memory.search_memory(session_id, searchPayload, limit=SEARCH_RESULT_LIMIT)

    summaries = [r for r in results if r.metadata.get('type') == 'summary']
    messages = [r for r in results if r.metadata.get('type') != 'summary']

    query_embedding = await zep_client.memory.acreate_embedding(query)
    summary_embeddings = [await zep_client.memory.acreate_embedding(s.content) for s in summaries]
    message_embeddings = [await zep_client.memory.acreate_embedding(m.content) for m in messages]

    selected_results = []
    current_tokens = 0
    summary_context_limit = int(max_tokens * SUMMARY_CONTEXT_PERCENTAGE)

    ranked_summaries = rank_by_relevance(query_embedding, summary_embeddings, summaries)

    for i, (summary, summary_relevance) in enumerate(ranked_summaries):
        if summary_relevance < RELEVANCE_THRESHOLD:
            break

        summary_start = summary.metadata['start_time']
        summary_end = summary.metadata['end_time']
        relevant_messages = [m for m in messages if summary_start <= m.created_at <= summary_end]

        ranked_messages = rank_by_relevance(query_embedding,
                                            [message_embeddings[messages.index(m)] for m in relevant_messages],
                                            relevant_messages)

        percentage = max(MIN_SUMMARY_PERCENTAGE, INITIAL_SUMMARY_PERCENTAGE - (i * SUMMARY_PERCENTAGE_REDUCTION))
        messages_to_include = int(len(ranked_messages) * percentage)

        for message, message_relevance in ranked_messages[:messages_to_include]:
            if message_relevance < RELEVANCE_THRESHOLD:
                break
            if current_tokens + len(message.content.split()) <= summary_context_limit:
                selected_results.append(message)
                current_tokens += len(message.content.split())
            else:
                break

        if current_tokens >= summary_context_limit:
            break

    remaining_messages = [m for m in messages if m not in selected_results]
    ranked_remaining = rank_by_relevance(query_embedding,
                                         [message_embeddings[messages.index(m)] for m in remaining_messages],
                                         remaining_messages)
    for message, relevance_score in ranked_remaining:
            if relevance_score < RELEVANCE_THRESHOLD:
                break
            if current_tokens + len(message.content.split()) <= max_tokens:
                selected_results.append(message)
                current_tokens += len(message.content.split())
            else:
                break

    return selected_results

def rank_by_relevance(query_embedding, candidate_embeddings, candidates):
    similarities = [cosine_similarity(query_embedding, emb) for emb in candidate_embeddings]
    ranked = sorted(zip(candidates, similarities), key=lambda x: x[1], reverse=True)
    return ranked

def cosine_similarity(v1, v2):
    if VECTOR_NORMALIZATION:
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)
    return np.dot(v1, v2)

# Error handling decorator
def handle_errors(func):
    async def wrapper(*args, **kwargs):
        for attempt in range(ERROR_RETRY_ATTEMPTS):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == ERROR_RETRY_ATTEMPTS - 1:
                    if ERROR_LOGGING_LEVEL == "detailed":
                        print(f"Error in {func.__name__}: {str(e)}")
                    return FALLBACK_RESPONSE
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return wrapper

# Apply error handling to key functions
generate_response = handle_errors(generate_response)
check_and_summarize = handle_errors(check_and_summarize)
create_summary = handle_errors(create_summary)

def extract_message_content(message):
    # Remove username from the start of the message
    return re.sub(r'^.*?: ', '', message).strip()


def is_valid_message(message):
    # Check if the message meets all criteria to be included in full_prompt
    if len(message) < 5:
        return False
    if message.lower() in ["hi", "hello", "hey"]:
        return False
    if message.startswith('/'):
        return False
    if message.startswith('bot,') or '<@' in message:
        return False
    if message.strip().endswith('?'):
        return False
    return True


# Rate limiting
def rate_limit(func):
    cooldowns = {}
    async def wrapper(ctx, *args, **kwargs):
        if ctx.author.id in cooldowns:
            remaining = COOLDOWN_DURATION - (datetime.now() - cooldowns[ctx.author.id]).total_seconds()
            if remaining > 0:
                await ctx.send(RATE_LIMIT_RESPONSE)
                return
        cooldowns[ctx.author.id] = datetime.now()
        return await func(ctx, *args, **kwargs)
    return wrapper

# Apply rate limiting to commands




@bot.command(name='search')
async def search(ctx, keyword: str):
    channel_id = str(ctx.channel.id)
    session_id = get_channel_session_id(channel_id)

    async with ZepClient(ZEP_API_URL, ZEP_API_KEY) as client:
        try:
            historical_messages = await client.message.aget_session_messages(
                session_id)
        except Exception as e:
            await ctx.send(f"Error retrieving historical messages: {e}")
            return

    search_results = []
    for msg in historical_messages:
        if keyword.lower() in msg.content.lower():
            highlighted_content = highlight_keyword(msg.content, keyword)
            search_results.append(f"**{msg.role}**: {highlighted_content}")

    if search_results:
        response = f"Search results for '{keyword}':\n\n" + "\n\n".join(
            search_results[-10:])
        if len(response) > 2000:
            response = response[:1997] + "..."
        await ctx.send(response)
    else:
        await ctx.send(f"No results found for '{keyword}'.")


@bot.command(name='prompt')
async def prompt(ctx):
    if not recent_prompts:
        await ctx.send("No recent prompts available.")
        return

    response = "Recent prompts:\n\n"
    for i, item in enumerate(reversed(recent_prompts), 1):
        response += f"{i}. Question: {item['question']}\n"
        response += f"   Prompt:\n{item['prompt_summary']}\n\n"

    chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
    for chunk in chunks:
        await ctx.send(chunk)




search = rate_limit(search)
prompt = rate_limit(prompt)


@bot.event
async def on_shutdown():
    await session_storage.close()

# Run the bot
if __name__ == "__main__":

    print("=================", dir(zep_client.memory))
    bot.run(os.getenv("DISCORD_BOT_TOKEN"), on_shutdown=on_shutdown)
