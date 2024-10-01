import subprocess

# Start bot.py
discord_process = subprocess.Popen(['python', 'discord_func.py'])

# Start run.py
telegram_process = subprocess.Popen(['python', 'telegram_func.py'])

slack_process = subprocess.Popen(['python', 'slack_func.py'])

whatsapp_process = subprocess.Popen(['python', 'whatsapp_test.py'])


# Wait for both scripts to complete
discord_process.wait()
telegram_process.wait()
slack_process.wait()
whatsapp_process.wait()

print('Assistant is running')