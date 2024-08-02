import logging
import os
from dotenv import load_dotenv
import traceback
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest
import openai
from zep_python import ZepClient, MemorySearchPayload
from zep_python.memory import Memory, Message
import uuid
import asyncio
from zep_python.exceptions import NotFoundError
import concurrent.futures
import re
import tiktoken

# Load environment variables
load_dotenv()

# # Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from environment variables
ZEP_API_URL = os.getenv("ZEP_API_URL")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize clients
openai.api_key = OPENAI_API_KEY
zep_client = ZepClient(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)




# Memory and Summarization
MAX_MESSAGES_BEFORE_SUMMARY = 75  # Number of messages before triggering a summary
MAX_CHARS_BEFORE_SUMMARY = 12000  # Total character count before triggering a summary
SUMMARY_WORD_LIMIT = 200  # Maximum word count for generated summaries
SUMMARY_MAX_AGE_HOURS = 24  # Maximum age of a summary before it's updated, regardless of message count
MAX_TOKENS_FOR_SUMMARY = 3000

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
                    chat_id BIGINT PRIMARY KEY,
                    session_id UUID NOT NULL
                )
            ''')

    async def get_session_id(self, chat_id: int) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT session_id FROM sessions WHERE chat_id = $1',
                chat_id
            )
            if row:
                return str(row['session_id'])
            
            # If no session exists, create a new one
            session_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO sessions (chat_id, session_id) VALUES ($1, $2)',
                chat_id, session_id
            )
            return session_id

    async def close(self):
        await self.pool.close()

session_storage = PostgresSessionStorage()






async def start(update: Update, context):
    await update.message.reply_text('Hello! I am your AI assistant. Mention me to ask questions. Use /search <keyword> to search chat logs.')

async def send_typing_periodically(context, chat_id):
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4)

async def thinking_animation(message: Message):
    text = "Thinking"
    dots = 0
    while True:
        try:
            dots = (dots % 3) + 1  # Cycle through 1, 2, 3 dots
            await message.edit_text(f"{text}{'.' * dots}")
            await asyncio.sleep(0.01)  # Wait for 0.1 seconds before the next update
        except BadRequest as e:
            if "Message is not modified" in str(e):
                continue  # If the message didn't change, just continue
            else:
                break  # If there's another kind of error, stop the animation
        except Exception:
            break  # If any other exception occurs, stop the animation



async def handle_message(update: Update, context):
    try:
        message = update.message
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        text = message.text

        logger.info(f"Received message: {text}")

        # Generate a session_id based on chat_id
        session_id = f"telegram_chat_{chat_id}"

        # Save message to Zep memory
        memory = Memory(
            messages=[Message(role="user", content=f"{user_id}: {text}")],
            metadata={"session_id": session_id}
        )
        logger.debug(f"Adding memory: {memory}")
        zep_client.memory.add_memory(session_id, memory)
        print(f"Message saved: {text}")

        # Check if bot is mentioned
        if context.bot.username in text:
            logger.info("Bot mentioned, generating response...")
            
            thinking_message = await update.message.reply_text("Thinking...")

            thinking_task = asyncio.create_task(thinking_animation(thinking_message))

            # Retrieve chat history
            try:
                messages = await zep_client.message.aget_session_messages(session_id)
                logger.info(f"Number of messages in chat history: {len(messages)}")
                chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])
            except NotFoundError:
                logger.info("Session not found, starting a new conversation")
                chat_history = ""

            gpt_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Chat history:\n{chat_history}\n\nUser: {text}"}
            ]

        
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=gpt_messages
            )

            reply_text = response.choices[0].message.content.strip()
            logger.info(f"Generated response: {reply_text}")

            # Send the generated response
            thinking_task.cancel()
            await thinking_message.edit_text(reply_text)
           
            # Save bot's response to Zep memory
            bot_memory = Memory(
                    messages=[Message(role="assistant", content=reply_text)],
                    metadata={"session_id": session_id}
                   
            )
            zep_client.memory.add_memory(session_id, bot_memory)
        else:
            logger.info("Bot not mentioned, no response generated.")

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        logger.error(traceback.format_exc())



async def search_chat(update: Update, context):
    if not context.args:
        await update.message.reply_text("Please provide a search keyword. Usage: /search <keyword>")
        return

    keyword = " ".join(context.args)
    chat_id = str(update.message.chat_id)
    session_id = f"telegram_chat_{chat_id}"

    search_payload = MemorySearchPayload(
        text=keyword,
        search_scope="messages",
        search_type="mmr", 
        mmr_lambda=0.5
    )

    try:
        search_message = await update.message.reply_text("Searching...")
        search_results = await zep_client.memory.asearch_memory(session_id, search_payload, limit=5)
        
        if search_results:
            response = "Search results:\n\n"
            for result in search_results:
                if result.message:
                    content = result.message.get('content', 'No content available')
                    # Highlight the keyword by making it uppercase and surrounding it with characters
                    highlighted_content = re.sub(
                        f'({re.escape(keyword)})',
                        lambda m: f"<<{m.group(1).upper()}>>",
                        content,
                        flags=re.IGNORECASE
                    )
                    response += f"{highlighted_content}\n\n"
        else:
            response = "No results found for the given keyword."

        await search_message.edit_text(response)
    except Exception as e:
        logger.error(f"Error in search_chat: {str(e)}")
        await update.message.reply_text("An error occurred while searching. Please try again later.")



def count_tokens(text: str) -> int:
    encoding = tiktoken.encoding_for_model(SUMMARIZATION_MODEL)
    return len(encoding.encode(text))

# async def summarize_chat(update: Update, context):
#     chat_id = str(update.message.chat_id)
#     session_id = f"telegram_chat_{chat_id}"

#     try:
#         # Retrieve recent messages
#         messages = await zep_client.message.aget_session_messages(session_id)
        
#         # Prepare the chat history for summarization
#         chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
#         # Truncate the chat history if it's too long
#         while count_tokens(chat_history) > MAX_TOKENS_FOR_SUMMARY:
#             messages = messages[1:]  # Remove the oldest message
#             chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])

#         # Generate summary
#         summary_message = await update.message.reply_text("Generating summary...")

#         response = await openai.ChatCompletion.acreate(
#             model=SUMMARIZATION_MODEL,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant tasked with summarizing conversations. Provide a concise summary of the key points discussed."},
#                 {"role": "user", "content": f"Please summarize the following conversation:\n\n{chat_history}"}
#             ]
#         )

#         summary = response.choices[0].message.content.strip()

#         # Send the summary
#         await summary_message.edit_text(f"Summary of recent conversation:\n\n{summary}")

#     except Exception as e:
#         logger.error(f"Error in summarize_chat: {str(e)}")
#         await update.message.reply_text("An error occurred while generating the summary. Please try again later.")




async def error_handler(update: Update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("search", search_chat)) 
    # application.add_handler(CommandHandler("summarize", summarize_chat))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()