import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from zep_python import ZepClient
import openai  # Assuming GPT-4-mini is accessible via OpenAI's API

load_dotenv()

ZEP_API_URL = os.getenv("ZEP_API_URL")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN= os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Initialize Zep client
zep_client = ZepClient(ZEP_API_URL, ZEP_API_KEY)



async def start(update: Update, context):
    await update.message.reply_text("Hello! I'm your Telegram bot. How can I help you?")

async def handle_message(update: Update, context):
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Store message in Zep
    zep_client.add_memory(str(chat_id), {
        "user_id": str(user_id),
        "message": user_message
    })

    # Retrieve chat history from Zep
    chat_history = zep_client.get_memory(str(chat_id))

    # Analyze chat history with GPT-4-mini
    prompt = f"Chat history: {chat_history}\n\nUser: {user_message}\nBot:"
    response = openai.Completion.create(
        engine="gpt-4o-mini",
        prompt=prompt,
        max_tokens=150
    )

    bot_response = response.choices[0].text.strip()

    # Send response back to user
    await update.message.reply_text(bot_response)

def main():
    application = Application.builder().token("").build()
    print("dsdffffffffffff", ZEP_API_KEY )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()