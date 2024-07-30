import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

openai.api_key = OPENAI_API_KEY

async def start(update, context):
    await update.message.reply_text("Hello! I'm a bot powered by OpenAI. How can I help you?")

async def handle_message(update, context):
    message = update.message.text
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=message,
        max_tokens=150
    )
    await update.message.reply_text(response.choices[0].text.strip())

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()