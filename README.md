Copilot Telegram Bot

<div align="center">  An intelligent Telegram bot based on Microsoft Copilot






</div>  📖 Table of Contents

About the Project

Features

Use Cases

Quick Start Guide

Usage Guide

Project Structure

Module Descriptions

Dependencies

Contributing

License



---

📖 About the Project

This project is a powerful Telegram bot that uses Microsoft Copilot to generate smart and accurate responses. The bot manages context intelligently by keeping a separate memory for each topic (thread), generating responses based on conversation context.

Key Features:

Uses Microsoft Copilot API for intelligent responses

Separate context management for each topic (thread)

Supports 4 languages (Persian, English, Russian, Arabic)

Multiple response modes (short, normal, full, code)

Private mode for sensitive conversations

Stores chat history in SQLite database

Channel membership verification system



---

✨ Features

📝 Smart Responses

Uses Microsoft Copilot for accurate and useful answers

Live streaming responses

Markdown support for formatted text and code


🌍 Multilingual Support

Persian (🇮🇷)

English (🇺🇸)

Russian (🇷🇺)

Arabic (🇸🇦)

Automatic language detection


📂 Context Management

Separate context per topic (thread)

Chat history storage

Topic summarization

View conversation history


🎛️ Response Modes

Short: brief and concise answers

Normal: balanced responses (default)

Full: detailed and comprehensive answers

Code: focused on programming and examples


🔒 Private Mode

No message storage in database

No use of chat history for context

Suitable for sensitive or one-time conversations


📊 Stats & History

Personal usage statistics

Message history per topic

Response generation time tracking


✅ Membership Verification

Channel membership verification system

Customizable channel settings



---

💡 Use Cases

📚 Education & Learning

Answer academic questions across disciplines

Explain complex concepts simply

Solve math, physics, and similar problems

Exam preparation


💻 Programming

Code debugging

Explaining algorithms and data structures

Writing and improving code

Suggesting best practices

Multi-language programming support


📝 Summarization & Writing

Summarizing long texts

Writing emails, articles, and content

Improving writing style

Grammar and spelling correction


🤝 General Advice

Everyday questions

Guidance across various topics

Idea and solution suggestions


🌐 Translation & Language

Translating between languages

Learning vocabulary and grammar

Improving language skills



---

🚀 Quick Start

Prerequisites

Before starting, make sure you have:

Python 3.8+

pip (Python package manager)

A Telegram bot token (from @BotFather)


Installation Steps

1. Clone the repository

git clone https://github.com/dezhcode/copilot-telegram-bot.git  
cd copilot-telegram-bot

2. Install dependencies

pip install -r requirements.txt

3. Configure environment variables

Create a .env file in the project root and add:

# Telegram bot token (required)  
BOT_TOKEN=your_bot_token_here  

# Worker settings (optional)  
USER_LLM_WORKERS=2  
NLP_LLM_WORKERS=1  
LLM_QUEUE_SIZE=200

4. Run the bot

python main.py

5. Start using

Find your bot on Telegram

Send /start

Choose your language

Verify channel membership

Start chatting



---

📖 Usage Guide

Main Commands

Command	Description

/start	Start the bot
/help	Show help menu
/lang	Change language
/settings	Show settings
/profile	View profile
/mode	Change response mode
/history	Current topic history
/reset	Clear current topic context
/reset_all	Clear all topics
/stats	View statistics
/about	About the bot


How to Use

1. Start chatting: just send a message


2. Reply context: replying to a message includes it in context


3. Change mode: use /mode or settings menu


4. View history: /history for current thread


5. Reset context: /reset clears current topic




---

📁 Project Structure

v 1/  
├── app/  
│   ├── __init__.py  
│   ├── bot.py  
│   ├── config.py  
│   ├── copilot_client.py  
│   ├── storage.py  
│   └── ui_texts.py  
├── main.py  
├── requirements.txt  
├── .gitignore  
├── LICENSE  
└── README.md


---

🔧 Module Descriptions

1. main.py

Entry point of the application:

Configures asyncio event loop

Calls run_bot() from app.bot

Starts the bot


2. app/config.py

Loads configuration from environment variables:

Config class

load_config() function

Default values handling


Environment variables:

BOT_TOKEN (required)

USER_LLM_WORKERS (default: 2)

NLP_LLM_WORKERS (default: 1)

LLM_QUEUE_SIZE (default: 200)


3. app/storage.py

Handles SQLite database:

StoredMessage class

Storage class

Manages users, messages, settings, summaries


Database tables:

users

chats

messages

thread_settings

profile_facts

topic_summaries

topic_message_ids


4. app/copilot_client.py

Manages Microsoft Copilot communication:

CopilotSession class

CopilotClient class

ask() for full responses

ask_stream() for streaming responses

WebSocket communication handling


5. app/ui_texts.py

UI text and localization:

Supported languages list

UI text dictionary

t() translation function

Keyboard builders


6. app/bot.py

Core bot logic:

Worker pool system

Request queue management

Aiogram dispatcher setup

Command handlers

Callback handlers

Message streaming logic

Context management

Channel membership verification



---

📦 Dependencies

Dependency	Version	Description

aiogram	>=3.0.0	Modern Telegram bot framework
aiohttp	>=3.8.0	Async HTTP client
requests	>=2.28.0	Sync HTTP client
websockets	>=11.0.0	WebSocket library



---

🤝 Contributing

Contributions are welcome!

1. Fork the repository


2. Create a new branch: git checkout -b feature/AmazingFeature


3. Commit changes: git commit -m 'Add AmazingFeature'


4. Push branch: git push origin feature/AmazingFeature


5. Open a Pull Request



Guidelines:

Document your code properly

Test before committing

Write clear commit messages

Update README if needed



---

📄 License

This project is licensed under the MIT License. See the LICENSE file for details.


---

👨‍💻 Developer

Dezhcode - GitHub



---

🙏 Acknowledgements

Microsoft Copilot for AI API

aiogram for Telegram bot framework

Everyone who reviews this project



---

Programmed by Dezhcode
