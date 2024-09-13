import os
import sys
import requests
import openai
import zep_python as zep
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2 import sql
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
WAHA_API_BASE_URL = os.getenv('WAHA_API_BASE_URL', 'https://waha.devlike.pro')
WAHA_API_KEY = os.getenv('WAHA_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ZEP_API_BASE_URL = os.getenv('ZEP_API_BASE_URL')

# PostgreSQL configuration
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Validate essential environment variables
required_env_vars = ['WAHA_API_KEY', 'OPENAI_API_KEY', 'ZEP_API_BASE_URL', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Initialize Zep client
try:
    zep_client = zep.ZepClient(base_url=ZEP_API_BASE_URL)
except Exception as e:
    logger.error(f"Failed to initialize Zep client: {e}")
    sys.exit(1)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise

def create_messages_table():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
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
        logger.info("Messages table created successfully or already exists.")
    except psycopg2.Error as e:
        logger.error(f"Failed to create messages table: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def log_message_to_postgres(group_id, sender, message):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("INSERT INTO messages (group_id, sender, message) VALUES (%s, %s, %s)"),
                    (group_id, sender, message)
                )
            conn.commit()
        logger.info(f"Logged message to PostgreSQL: {message[:50]}... from {sender} in group {group_id}")
    except psycopg2.Error as e:
        logger.error(f"Failed to log message to PostgreSQL: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def log_message_to_zep(message, sender, group_id):
    try:
        session_id = group_id
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
        logger.info(f"Logged message to Zep: {message[:50]}... from {sender} in group {group_id}")
    except Exception as e:
        logger.error(f"Failed to log message to Zep: {e}")
        raise

def retrieve_chat_history(session_id):
    try:
        messages = zep_client.get_messages(session_id)
        return messages
    except zep.SessionNotFound:
        logger.warning(f"No chat history found for session {session_id}")
        return []
    except Exception as e:
        logger.error(f"Failed to retrieve chat history: {e}")
        return []

def build_contextual_prompt(current_message, group_id):
    history = retrieve_chat_history(group_id)
    history_content = "\n".join(
        [f"{msg.metadata['sender']}: {msg.content}" for msg in history if msg.content]
    )
    
    prompt = f"Conversation history:\n{history_content}\n\nUser's latest message:\n{current_message}\n\nReply to the user based on the conversation above."
    return prompt

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info(f"Message sent successfully to group {group_id}")
        return response.status_code, response.text
    except requests.RequestException as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def handle_mention(message, group_id):
    prompt = build_contextual_prompt(message, group_id)
    
    try:
        response = openai.Completion.create(
            engine="gpt-4o-mini",
            prompt=prompt,
            max_tokens=150
        )
        
        reply = response['choices'][0]['text'].strip()
        logger.info(f"Generated response for group {group_id}")
        return reply
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "Sorry, I'm having trouble thinking right now. Please try again later."
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "An unexpected error occurred. Please try again later."

def process_messages():
    url = f"{WAHA_API_BASE_URL}/getMessages"
    headers = {
        'Authorization': f'Bearer {WAHA_API_KEY}',
        'Content-Type': 'application/json'
    }

    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            messages = response.json()

            for msg in messages:
                group_id = msg['group_id']
                sender = msg['sender']
                message = msg['message']


                # group_id = msg['group_id']
                # sender = msg['sender']
                # message = msg['message']

                try:
                    log_message_to_postgres(group_id, sender, message)
                    log_message_to_zep(message, sender, group_id)

                    if 'bot_name' in message:  # Replace 'bot_name' with your bot's identifier
                        reply = handle_mention(message, group_id)
                        send_whatsapp_message(group_id, reply)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue  # Continue with the next message even if there's an error

        except requests.RequestException as e:
            logger.error(f"Error fetching messages from WAHA API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in message processing loop: {e}")
        
        # Add a small delay to avoid hammering the API
        time.sleep(1)

if __name__ == "__main__":
    try:
        create_messages_table()
        logger.info("Starting message processing...")
        process_messages()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)