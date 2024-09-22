import logging
from abc import ABC, abstractmethod
from zep_integration import ZepIntegration
import openai
from config import *

class ChatBot(ABC):
    def __init__(self, zep_integration: ZepIntegration, openai_api_key: str):
        self.zep = zep_integration
        openai.api_key = openai_api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def start(self, *args, **kwargs):
        pass

    @abstractmethod
    async def handle_message(self, *args, **kwargs):
        pass

    @abstractmethod
    async def search_chat(self, *args, **kwargs):
        pass

    async def generate_response(self, chat_id: str, user_message: str):
        context = await self.zep.get_relevant_context(chat_id, user_message, MAX_CONTEXT_TOKENS)
        
        gpt_messages = [
            {"role": "system", "content": "You are a helpful assistant. Use the provided context to inform your responses."},
            {"role": "user", "content": f"Context:\n{context}\n\nUser message: {user_message}"}
        ]

        response = await openai.ChatCompletion.acreate(
            model=RESPONSE_GENERATION_MODEL,
            messages=gpt_messages
        )

        return response.choices[0].message.content.strip()

    async def check_and_summarize(self, chat_id: str):
        messages = await self.zep.get_chat_history(chat_id)
        if len(messages) >= MAX_MESSAGES_BEFORE_SUMMARY:
            await self.zep.create_summary(chat_id, messages)