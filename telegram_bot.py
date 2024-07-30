import logging
import os
from dotenv import load_dotenv
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import openai
from zep_python import ZepClient
from zep_python.memory import Memory, Message

# Load environment variables
load_dotenv()

# Set up logging
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


async def handle_message(update: Update, context):
    try:
        message = update.message
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        text = message.text

        logger.info(f"Received message: {text}")

        # Save message to Zep memory
        memory = Memory(
            messages=[
                Message(
                    role="user",
                    content=text,
                    metadata={"user_id": user_id}
                )
            ]
        )
        logger.debug(f"Adding memory: {memory}")
        zep_client.memory.add_memory(chat_id, memory)

        # Check if bot is mentioned
        if context.bot.username in text:
            logger.info("Bot mentioned, generating response...")
            # Retrieve chat history
            memory_content = zep_client.memory.get_memory(chat_id)
            messages = memory_content.messages if memory_content else []
            chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])

            # Prepare messages for GPT-3.5-turbo
            gpt_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Chat history:\n{chat_history}\n\nUser: {text}"}
            ]

            # Generate response using GPT-3.5-turbo
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=gpt_messages
            )

            reply_text = response.choices[0].message.content.strip()
            logger.info(f"Generated response: {reply_text}")

            # Send the generated response
            await update.message.reply_text(reply_text)

            # Save bot's response to Zep memory
            bot_memory = Memory(
                messages=[
                    Message(
                        role="assistant",
                        content=reply_text,
                        metadata={"user_id": str(context.bot.id)}
                    )
                ]
            )
            zep_client.memory.add_memory(chat_id, bot_memory)
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