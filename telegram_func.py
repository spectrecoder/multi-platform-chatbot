import logging
import os
from dotenv import load_dotenv
import traceback
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest
import openai
from zep_python import ZepClient
from zep_python.memory import Memory, Message
import uuid
import asyncio

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

async def start(update: Update, context):
    await update.message.reply_text('Hello! I am your AI assistant. Mention me to ask questions.')

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

async def error_handler(update: Update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()