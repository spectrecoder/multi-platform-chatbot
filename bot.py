import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from zep_python import ZepClient
import openai

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables
ZEP_API_URL = os.getenv('ZEP_API_URL')
ZEP_API_KEY = os.getenv('ZEP_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Debug logging
logger.info(f"ZEP_API_URL: {ZEP_API_URL}")
logger.info(f"ZEP_API_KEY: {'Set' if ZEP_API_KEY else 'Not set'}")
logger.info(f"OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not set'}")
logger.info(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not set'}")

# Initialize Zep client
if ZEP_API_URL and ZEP_API_KEY:
    try:
        zep_client = ZepClient(base_url=ZEP_API_URL, api_key=ZEP_API_KEY)
        logger.info("Zep client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Zep client: {str(e)}")
        zep_client = None
else:
    logger.error("ZEP_API_URL or ZEP_API_KEY not set")
    zep_client = None

# Initialize OpenAI client
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    logger.info("OpenAI API key set")
else:
    logger.error("OPENAI_API_KEY not set")

async def start(update: Update, context):
    await update.message.reply_text("Hello! I'm your Telegram bot. How can I help you?")

async def handle_message(update: Update, context):
    if not zep_client:
        await update.message.reply_text("Sorry, I'm having trouble with my memory. Please try again later.")
        return

    user_message = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Store message in Zep
    try:
        zep_client.add_memory(str(chat_id), {
            "user_id": str(user_id),
            "message": user_message
        })
    except Exception as e:
        logger.error(f"Error adding memory to Zep: {str(e)}")
        await update.message.reply_text("Sorry, I'm having trouble remembering our conversation. Please try again.")
        return

    # Retrieve chat history from Zep
    try:
        chat_history = zep_client.get_memory(str(chat_id))
    except Exception as e:
        logger.error(f"Error retrieving memory from Zep: {str(e)}")
        await update.message.reply_text("Sorry, I'm having trouble recalling our conversation. Please try again.")
        return

    # Analyze chat history with GPT-4-mini
    try:
        prompt = f"Chat history: {chat_history}\n\nUser: {user_message}\nBot:"
        response = openai.Completion.create(
            engine="gpt-4-mini",
            prompt=prompt,
            max_tokens=150
        )
        bot_response = response.choices[0].text.strip()
    except Exception as e:
        logger.error(f"Error generating response with OpenAI: {str(e)}")
        await update.message.reply_text("Sorry, I'm having trouble thinking of a response. Please try again.")
        return

    # Send response back to user
    await update.message.reply_text(bot_response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting bot")
    application.run_polling()

if __name__ == '__main__':
    main()