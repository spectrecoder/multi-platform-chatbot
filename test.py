import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import openai
from dotenv import load_dotenv
import logging
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

openai.api_key = OPENAI_API_KEY

async def start(update, context):
    logging.info(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text("Hello! I'm an AI assistant. How can I help you?")

async def handle_message(update, context):
    if context.bot.name.lower() not in update.message.text.lower():
        return

    
    message = update.message.text
    logging.info(f"Received message from user {update.effective_user.id}: {update.message.text}")
    
    thinking_message = await update.message.reply_text("Thinking...")
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message}
                ]
            )
        )
        reply = response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in OpenAI API call: {e}")
        reply = "I'm sorry, but I encountered an error while processing your request."

    # Edit the "Thinking..." message with the actual reply
    await thinking_message.edit_text(reply)

def main():
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.run_polling()
    except Exception as e:
        print(f"An error occurred in main: {e}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")