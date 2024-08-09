import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_bot()
        # self.start_bot()

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"bot.py has been modified. Restarting bot...")
            self.restart_bot()

    def start_bot(self):
        self.process = subprocess.Popen(['/New Work/mutil-platform-chatbot/venv/Scripts/python.exe', 'slack_func.py'])

    def restart_bot(self):
        if self.process:
            self.process.terminate()
            # self.process.terminate()
            self.process.wait()
        self.start_bot()

if __name__ == "__main__":
    path = '.'
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()