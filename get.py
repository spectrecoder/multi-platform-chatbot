import os

from multibot import Message, TelegramBot

telegram_bot = TelegramBot(
    api_id="23019945",
    api_hash="fd2402d60c7539a1ac485ce011ec1747",
    bot_token="7441428802:AAF4VxuMJCiVts27ihaNsKynmTralXGjbJo"
)


@telegram_bot.register('hello')
async def function_name_1(message: Message):
    await telegram_bot.send('Hi!', message)


# telegram_bot.start()

print(telegram_bot.string_sessions)