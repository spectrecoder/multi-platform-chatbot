from zep_python import ZepClient
from zep_python.memory import Memory, Message
import openai
import discord
import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
import re
import io
import requests
import uuid
from datetime import datetime
from discord.ext import commands
from discord import Embed, Colour
import os
from dotenv import load_dotenv
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

user_languages = {}
default_language = 'en'

openai.api_key = os.getenv("OPENAI_API_KEY")
ZEP_API_URL = os.getenv("ZEP_API_URL")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=os.getenv('BOT_PREFIX'),
                   intents=intents,
                   help_command=None)

zep_client = ZepClient(ZEP_API_URL, ZEP_API_KEY)

recent_prompts = []


def get_channel_session_id(channel_id):
    filename = "channel_sessions.txt"
    try:
        with open(filename, "r") as f:
            for line in f:
                saved_channel_id, session_id = line.strip().split(",")
                if saved_channel_id == str(channel_id):
                    return session_id
    except FileNotFoundError:
        pass

    session_id = str(uuid.uuid4())
    with open(filename, "a") as f:
        f.write(f"{channel_id},{session_id}\n")
    return session_id


def highlight_keyword(text, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(f"*`{keyword}`*", text)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = str(message.channel.id)
    content = message.content
    session_id = get_channel_session_id(channel_id)

    try:
        memory = Memory(messages=[
            Message(role="user", content=f"{message.author.name}: {content}")
        ],
                        metadata={"session_id": session_id})
        zep_client.memory.add_memory(session_id, memory)
        print(f"Message saved: {content}")
    except Exception as e:
        print(f"Error saving message: {e}")

    if bot.user.mentioned_in(message) or message.content.lower().startswith(
            'bot,'):
        clean_content = message.content.replace(f'<@{bot.user.id}>',
                                                '').strip()
        clean_content = clean_content[4:] if clean_content.lower().startswith(
            'bot,') else clean_content

        thinking_message = await message.channel.send("Thinking...")

        async with message.channel.typing():
            response = await generate_response(channel_id, clean_content)

            chunks = [
                response[i:i + 2000] for i in range(0, len(response), 2000)
            ]

            await thinking_message.edit(content=chunks[0])

            for chunk in chunks[1:]:
                await message.channel.send(chunk)

        try:
            memory = Memory(
                messages=[Message(role="assistant", content=response)],
                metadata={"session_id": session_id})
            zep_client.memory.add_memory(session_id, memory)
            print(f"Bot response saved: {response}")
        except Exception as e:
            print(f"Error saving bot response: {e}")

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

    for memory in historical_messages[-1000:]:
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


@bot.command(name='search')
async def search(ctx, *, keyword):
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
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
