import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, Response
import openai
from zep_python import ZepClient
import threading
import time

# import time
# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Set OpenAI API key
openai.api_key = os.environ["OPENAI_API_KEY"]

# Initialize Zep client
zep_client = ZepClient(base_url=os.environ["ZEP_API_URL"], api_key=os.environ["ZEP_API_KEY"])

# Initialize Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


def get_chat_history(channel_id):
    # Implement logic to retrieve chat history from Zep
    # This is a placeholder and needs to be implemented based on Zep's API
    return "Chat history placeholder"

# Function to generate response using OpenAI
def generate_response(prompt, history):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful Slack bot."},
            {"role": "user", "content": f"Chat history: {history}\n\nUser question: {prompt}"}
        ]
    )
    return response.choices[0].message['content']

# Function to simulate typing effect
def typing_effect(channel):
    app.client.chat_postMessage(channel=channel, text="Bot is typing...")

# Event listener for mentions

@app.event("app_mention")
def handle_mention(event, say):
    channel_id = event["channel"]
    user_id = event["user"]
    text = event["text"]

 
    threading.Thread(target=typing_effect, args=(channel_id,)).start()


    history = get_chat_history(channel_id)

    # Generate response
    response = generate_response(text, history)

 
    try:
        
        app.client.chat_delete(channel=channel_id, ts=event["ts"])
    except Exception as e:
        print(f"Error deleting typing message: {e}")
    # except Exception as e:
    #     print(f"Error deleting typing message: {e}")

   
    say(text=response)


# Flask route for Slack events
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Main execution
if __name__ == "__main__":
    print("Starting the Slack bot server...")
    flask_app.run(port=5001)