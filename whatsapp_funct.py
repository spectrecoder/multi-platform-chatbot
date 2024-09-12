import os
import requests
import openai
import zep_python as zep
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2 import sql

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
WAHA_API_BASE_URL = 'https://waha.devlike.pro'
WAHA_API_KEY = os.getenv('WAHA_API_KEY')  # Loaded from .env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Loaded from .env
ZEP_API_BASE_URL = os.getenv('ZEP_API_BASE_URL')  # Loaded from .env

# PostgreSQL configuration
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Initialize Zep client
zep_client = zep.ZepClient(base_url=ZEP_API_BASE_URL)

# Function to create PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# Function to create the messages table if it doesn't exist
def create_messages_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            group_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Function to log messages to PostgreSQL
def log_message_to_postgres(group_id, sender, message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("INSERT INTO messages (group_id, sender, message) VALUES (%s, %s, %s)"),
        (group_id, sender, message)
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Logged message to PostgreSQL: {message} from {sender} in group {group_id}")

# Function to log messages to Zep
def log_message_to_zep(message, sender, group_id):
    session_id = group_id  # Use group ID as the session ID
    
    try:
        session = zep_client.get_session(session_id)
    except zep.SessionNotFound:
        session = zep.Session(session_id=session_id, metadata={"group_name": group_id})
        zep_client.add_session(session)
    
    chat_message = zep.Message(
        role="user",
        content=message,
        metadata={
            "sender": sender,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    zep_client.add_message(session_id, chat_message)
    print(f"Logged message to Zep: {message} from {sender} in group {group_id}")

# Function to retrieve chat history from Zep
def retrieve_chat_history(session_id):
    try:
        messages = zep_client.get_messages(session_id)
        return messages
    except zep.SessionNotFound:
        return []

# Function to build a prompt using past messages from Zep
def build_contextual_prompt(current_message, group_id):
    history = retrieve_chat_history(group_id)
    history_content = "\n".join(
        [f"{msg.metadata['sender']}: {msg.content}" for msg in history if msg.content]
    )
    
    prompt = f"Conversation history:\n{history_content}\n\nUser's latest message:\n{current_message}\n\nReply to the user based on the conversation above."
    return prompt

# Function to send a message via Waha API
def send_whatsapp_message(group_id, message):
    url = f"{WAHA_API_BASE_URL}/sendMessage"
    headers = {
        'Authorization': f'Bearer {WAHA_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "group_id": group_id,
        "message": message
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.text

# Function to handle message when bot is mentioned, with chat log analysis
def handle_mention(message, group_id):
    prompt = build_contextual_prompt(message, group_id)
    
    try:
        response = openai.Completion.create(
            engine="gpt-4o-mini",
            prompt=prompt,
            max_tokens=150
        )
        
        reply = response['choices'][0]['text'].strip()
        return reply
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I'm having trouble thinking right now."

# Main loop to receive and process messages
def process_messages():
    url = f"{WAHA_API_BASE_URL}/getMessages"
    headers = {
        'Authorization': f'Bearer {WAHA_API_KEY}',
        'Content-Type': 'application/json'
    }

    while True:
        try:
            response = requests.get(url, headers=headers)
            messages = response.json()

            for msg in messages:
                group_id = msg['group_id']
                sender = msg['sender']
                message = msg['message']

                # Log the message to both PostgreSQL and Zep
                log_message_to_postgres(group_id, sender, message)
                log_message_to_zep(message, sender, group_id)

                if 'bot_name' in message:  # Replace 'bot_name' with your bot's identifier
                    reply = handle_mention(message, group_id)
                    send_whatsapp_message(group_id, reply)

        except Exception as e:
            print(f"Error processing messages: {e}")

if __name__ == "__main__":
    create_messages_table()
    process_messages()