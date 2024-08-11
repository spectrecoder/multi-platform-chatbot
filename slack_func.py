import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
from zep_python import ZepClient

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
    try:
        # Retrieve the memory for the channel
        memory = zep_client.get_memory(channel_id)
        
        # Extract and format the chat history
        history = []
        for message in memory.messages:
            history.append(f"{message.role}: {message.content}")
        
        return "\n".join(history)
    except Exception as e:
        print(f"Error retrieving chat history: {e}")
        return "Error retrieving chat history"

def save_message_to_zep(channel_id, role, content):
    try:
        zep_client.add_memory(
            session_id=channel_id,
            memory={
                "role": role,
                "content": content
            }
        )
    except Exception as e:
        print(f"Error saving message to Zep: {e}")

# Function to generate response using OpenAI
def generate_response(prompt, history):
    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[
            {"role": "system", "content": "You are a helpful Slack bot. Analyze the chat history and provide a relevant response."},
            {"role": "user", "content": f"Chat history:\n{history}\n\nUser question: {prompt}"}
        ]
    )
    return response.choices[0].message['content']

# Event listener for mentions
@app.event("app_mention")
def handle_mention(event, say):
    channel_id = event["channel"]
    user_id = event["user"]
    text = event["text"]

    # Save the user's message to Zep
    save_message_to_zep(channel_id, "user", text)

    # Get chat history
    history = get_chat_history(channel_id)

    # Generate response
    response = generate_response(text, history)

    # Save the bot's response to Zep
    save_message_to_zep(channel_id, "assistant", response)

    # Post the response
    say(text=response)

# Flask route for Slack events
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Main execution
if __name__ == "__main__":
    print("Starting the Slack bot server...")
    flask_app.run(port=5001)