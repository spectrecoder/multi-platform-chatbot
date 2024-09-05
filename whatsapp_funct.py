import requests
import json
import openai

# Configuration
WAHA_API_BASE_URL = 'https://waha.devlike.pro'
WAHA_API_KEY = 'waha_api_key'  # 
OPENAI_API_KEY = 'openai_api_key'  

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Function to log messages
def log_message(message, sender, group_id):
    with open("group_messages.log", "a") as log_file:
        log_file.write(f"Group: {group_id}, Sender: {sender}, Message: {message}\n")

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

# Function to handle message when bot is mentioned
def handle_mention(message, group_id):
    # Use OpenAI GPT-4o-mini to generate a reply
    try:
        response = openai.Completion.create(
            engine="gpt-4o-mini",
            prompt=message,
            max_tokens=50
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
            # Fetch new messages from the group
            response = requests.get(url, headers=headers)
            messages = response.json()

            for msg in messages:
                group_id = msg['group_id']
                sender = msg['sender']
                message = msg['message']

                # Log the message
                log_message(message, sender, group_id)

                # Check if the bot is mentioned
                if 'bot_name' in message:  # Replace 'bot_name' with your bot's identifier
                    reply = handle_mention(message, group_id)
                    send_whatsapp_message(group_id, reply)

        except Exception as e:
            print(f"Error processing messages: {e}")

# Start the bot
if __name__ == "__main__":
    process_messages()
