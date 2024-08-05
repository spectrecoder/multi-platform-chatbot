import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import openai

# Load environment variables
load_dotenv()

# Set up Slack app
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
app = App(token=SLACK_BOT_TOKEN)


openai.api_key = os.getenv("OPENAI_API_KEY")

# Event listener for messages
@app.message(".*")
def handle_message(message, say):
    # Get the user's message
    user_message = message['text']

    # Generate a response using OpenAI
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"User: {user_message}\nBot:",
        max_tokens=150,
        n=1,
        stop=None,
        temperature=0.7,
    )

    # Send the response back to Slack
    bot_reply = response.choices[0].text.strip()
    say(bot_reply)


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()