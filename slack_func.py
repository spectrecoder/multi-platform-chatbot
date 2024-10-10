import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
from zep_python import ZepClient, MemorySearchPayload
from zep_python.memory import Memory, Message
# from zep_python.client import AsyncZep
# from zep_python.types import Message
from datetime import datetime
import logging
import traceback


# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Set OpenAI API key
openai.api_key = os.environ["OPENAI_API_KEY"]

# Initialize Zep client
zep_client = AsyncZep(base_url=os.environ["ZEP_API_URL"], api_key=os.environ["ZEP_API_KEY"])

# Initialize Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# Constants
RESPONSE_GENERATION_MODEL = "gpt-4o-mini"

def get_session_messages(session_id: str):
    try:
        messages = zep_client.message.get_session_messages(session_id)
        return messages
    except Exception as e:
        logger.error(f"Error retrieving session messages: {str(e)}")
        return []

def add_memory(session_id: str, memory: Memory):
    try:
        zep_client.memory.add_memory(session_id, memory)
    except Exception as e:
        logger.error(f"Error adding memory: {str(e)}")

@app.event("message")
def handle_message(event, say):
    try:
        channel_id = event["channel"]
        user_id = event.get("user", "Unknown")
        text = event.get("text", "")
        timestamp = datetime.fromtimestamp(float(event["ts"])).strftime("%Y.%m.%d")

        logger.info(f"Received message in channel {channel_id} from user {user_id}: {text}")

        # Generate a session_id based on channel_id
        session_id = f"slack_chat_{channel_id}"

@app.event("message")
def handle_message(event, say):
    try:
        channel_id = event["channel"]
        user_id = event.get("user", "Unknown")
        text = event.get("text", "")
        timestamp = datetime.fromtimestamp(float(event["ts"])).strftime("%Y.%m.%d")

        logger.info(f"Received message in channel {channel_id} from user {user_id}: {text}")

        # Generate a session_id based on channel_id
        session_id = f"slack_chat_{channel_id}"

        # Save message to Zep memory
        user_memory = Memory(
            messages=[Message(role="user", content=f"{user_id} ({timestamp}): {text}", timestamp=timestamp)],
            metadata={"session_id": session_id}
        )
        add_memory(session_id, user_memory)

        # Check if the bot is mentioned
        if app.client.auth_test()["user_id"] in text:
            handle_bot_mention(event, say, session_id)

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        logger.error(traceback.format_exc())


def handle_bot_mention(event, say, session_id):
    try:
        channel_id = event["channel"]
        text = event["text"]

        thinking_message = say("Thinking...")

        # Retrieve chat history
        messages = get_session_messages(session_id)
        chat_history = "\n".join([f"{m.role}: {m.content}" for m in messages])

        gpt_messages = [
            {"role": "system", "content": "You are a helpful Slack assistant."},
            {"role": "user", "content": f"Chat history:\n{chat_history}\n\nUser: {text}"}
        ]

        response = openai.ChatCompletion.create(
            model=RESPONSE_GENERATION_MODEL,
            messages=gpt_messages
        )

        reply_text = response.choices[0].message.content.strip()

        # Update the thinking message with the generated response
        app.client.chat_update(
            channel=channel_id,
            ts=thinking_message['ts'],
            text=reply_text
        )

        current_timestamp = datetime.utcnow().strftime("%Y.%m.%d")
        # Save bot's response to Zep memory
        bot_memory = Memory(
            messages=[Message(role="assistant", content=f"({current_timestamp}): {reply_text}", timestamp=current_timestamp)],
            metadata={"session_id": session_id}
        )
        add_memory(session_id, bot_memory)

    except Exception as e:
        logger.error(f"Error in handle_bot_mention: {str(e)}")
        logger.error(traceback.format_exc())
        say("An error occurred while processing your request. Please try again later.")

@app.command("/search")
def search_chat(ack, respond, command):
    ack()
    
    keyword = command['text']
    channel_id = command['channel_id']
    session_id = f"slack_chat_{channel_id}"

    if not keyword:
        respond("Please provide a search keyword. Usage: /search <keyword>")
        return

    search_payload = MemorySearchPayload(
        text=keyword,
        search_scope="messages",
        search_type="mmr",
        mmr_lambda=0.5
    )

    try:
        search_results = zep_client.memory.search_memory(session_id, search_payload, limit=5)
        
        if search_results:
            response = "Search results:\n\n"
            for result in search_results:
                if result.message:
                    content = result.message.get('content', 'No content available')
                    response += f"{content}\n\n"
        else:
            response = "No results found for the given keyword."

        respond(response)
    except Exception as e:
        logger.error(f"Error in search_chat: {str(e)}")
        respond("An error occurred while searching. Please try again later.")

# Flask route for Slack events
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


# Main execution
if __name__ == "__main__":
    print("Starting the Slack bot server...")
    flask_app.run(port=5001)

