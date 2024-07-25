# Multi Platform & Purpose AI assistant

Imagine having an AI assistant in every chatroom your business operates, seamlessly integrated into Slack, WhatsApp, Telegram, Discord, and more. Our AI bots give your team superpowers, streamline communication, and empower management to make informed decisions without constantly monitoring every conversation. With advanced searchability and custom functions tailored to your business needs, our solution transforms how your organization collaborates and operates.

Our AI integration service places intelligent bots into any chat platform your business uses, enhancing team productivity and providing management with the tools to make better decisions effortlessly.

## Features

- **Multi-Platform Integration**: Our AI bots can be integrated into popular chat platforms like Slack, WhatsApp, Telegram, Discord, and more, ensuring seamless adoption across your organization.
- **Enhanced Communication**: AI-powered bots assist in conversations by providing real-time information, answering queries, and facilitating smoother communication among team members.
- **Effortless Decision-Making**: Our solution allows for advanced search capabilities, making it easy for management to retrieve and analyze relevant information without sifting through endless chat logs.
- **Custom Functions**: Tailor the AI to fit specific business needs with custom functions,

## Commands

- `/help`: Display a list of available commands.
- `/search [query]`: Search your conversation history.
- `/setlang <lang_code>`: Set your preferred language (e.g., en, es, fr, de).
- `/checklang`: Check your current language setting.
- `/weather <location>`: Get weather information for a specified location.
- `/crypto <coin name>`: Get information about a cryptocurrency.
- `/events <area> <event_type>`: Get events from Ticketmaster in the specified area and optionally of a specific type.
- `/news <description>`: Get news articles related to the given description.

## Setup

1. Clone this repository.
2. Install the required dependencies:
3. Set up a `.env` file in the root directory with the following variables:
<h6>
</p>
DISCORD_TOKEN=your_discord_bot_token</p>
OPENAI_API_KEY=your_openai_api_key</p>
NEWSDATA_API_KEY=your_newsdata_api_key</p>
ZEP_API_URL=your_zep_api_url</p>
ZEP_API_KEY=your_zep_api_key</p>
OPENWEATHER_API_KEY=your_openweather_api_key</p>
TICKETMASTER_API_KEY=your_ticketmaster_api_key</p>
BOT_PREFIX=/</p>
SUPPORTED_LANGUAGES=en,es,fr,de</p>
</h6>
4. Run the bot

## Usage

- Mention the bot or start your message with 'bot,' to chat with it.
- Use the commands listed above to access specific functionalities.

## Dependencies

- discord.py
- python-dotenv
- requests
- openai
- aiohttp
- tenacity
- zep-python

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to check [issues page](https://github.com/Kevine0921/mutil-platform-chatbot/issues) if you want to contribute.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Contact

Contact👉- shottree657@gmail.com

Project Link: [https://github.com/Kevine0921](https://github.com/Kevine0921/mutil-platform-chatbot)
