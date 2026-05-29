# Copilot Free

<div align="center">

<img src="image/Copilot-free.jpg" alt="Copilot Free Logo" width="220" />

**Copilot Free** — a smart Telegram bot powered by Microsoft Copilot  
[@CopilotFreeBot](https://t.me/CopilotFreeBot) • [Channel](https://t.me/Dezhcode)

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0)](https://aiogram.dev/)
[![Telegram](https://img.shields.io/badge/Telegram-@CopilotFreeBot-26A5E4?logo=telegram&logoColor=white)](https://t.me/CopilotFreeBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-2EA44F)](LICENSE)

</div>

Language: **English** • [فارسی](README.fa.md)

<a name="quick-start"></a>
## 🚀 Quick Start
- Install: `pip install -r requirements.txt`
- Set token: `BOT_TOKEN=...`
- Run: `python main.py`

<a name="toc"></a>
## 🧭 Contents
- [About](#about)
- [Features](#features)
- [Use Cases](#use-cases)
- [Install & Run](#install--run)
- [Configuration](#configuration)
- [Bot Commands](#bot-commands)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Modules](#modules)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

---

<a name="about"></a>
## 📖 About
Copilot Free is a Telegram bot that generates answers using Microsoft Copilot. It keeps **separate context per topic/thread**, so conversations don’t mix and responses stay relevant.

**Links**
- Bot: [@CopilotFreeBot](https://t.me/CopilotFreeBot)
- Channel: [Dezhcode](https://t.me/Dezhcode)

---

<a name="features"></a>
## ✨ Features
- Multi-language: Persian, English, Russian, Arabic
- Separate context per topic + stored history (SQLite)
- Streaming responses (gradual updates in Telegram)
- Reply modes: short / normal / detailed / code
- Private mode for sensitive chats (no DB storage, no history context)
- Conversation utilities (history/reset/stats)
- Channel membership verification

---

<a name="use-cases"></a>
## 💡 Use Cases
- General Q&A and daily assistance
- Programming help (debugging, code explanations, code snippets)
- Summarization, rewriting, improving text
- Translation and language practice

---

<a name="install--run"></a>
## 🧰 Install & Run

### 1) Get the project
```bash
git clone <REPO_URL>
cd <REPO_DIR>
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Set BOT_TOKEN and run
This project reads configuration from **environment variables**.

**Windows (PowerShell)**
```powershell
$env:BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
python main.py
```

**Linux/macOS**
```bash
export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
python main.py
```

Note: If you use a `.env` file, make sure your runtime actually loads it (this project does not automatically read `.env` by itself).

---

<a name="configuration"></a>
## ⚙️ Configuration

| Variable | Default | Description |
|---|---:|---|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `USER_LLM_WORKERS` | `2` | Worker count for normal user messages |
| `NLP_LLM_WORKERS` | `1` | Worker count for higher priority / heavier jobs |
| `LLM_QUEUE_SIZE` | `200` | Request queue capacity |

---

<a name="bot-commands"></a>
## 🧾 Bot Commands

| Command | Description |
|---|---|
| `/start` | Start + language selection |
| `/help` | Help & menu |
| `/lang` | Change language |
| `/settings` | Settings (reply mode, time, private mode) |
| `/mode` | Change reply mode |
| `/history` | Current topic history |
| `/reset` | Clear current topic context |
| `/reset_all` | Clear all topics |
| `/stats` | User stats |
| `/about` | About the bot |

---

<a name="how-it-works"></a>
## 🔎 How It Works
High-level flow:
1. Receives a user message (if it’s a reply, the replied message is included)
2. Loads topic history from SQLite (unless private mode is enabled)
3. Enqueues the request and processes it using worker pools
4. Sends the prompt to Copilot and receives a streaming response
5. Updates Telegram message(s) and saves the result (unless private mode is enabled)

---

<a name="project-structure"></a>
## 📁 Project Structure
```
DezhCode/
├── app/
│   ├── bot.py
│   ├── config.py
│   ├── copilot_client.py
│   ├── storage.py
│   └── ui_texts.py
├── image/
│   └── Copilot-free.jpg
├── main.py
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

<a name="modules"></a>
## 🧩 Modules

<details>
<summary><strong>main.py</strong> — entry point</summary>

- Runs `run_bot()` and starts the asyncio loop.
</details>

<details>
<summary><strong>app/config.py</strong> — configuration loader</summary>

- Reads environment variables and applies safe minimums for worker/queue values.
</details>

<details>
<summary><strong>app/copilot_client.py</strong> — Copilot connectivity</summary>

- Starts a Copilot conversation and sends messages via WebSocket.
- Streams partial text as it arrives.
</details>

<details>
<summary><strong>app/storage.py</strong> — SQLite storage</summary>

- Stores users, messages, topic settings, and summaries.
- Provides history for better prompts.
</details>

<details>
<summary><strong>app/ui_texts.py</strong> — texts & keyboards</summary>

- Multi-language UI texts and inline keyboards (language/join/menu).
</details>

<details>
<summary><strong>app/bot.py</strong> — bot logic</summary>

- Command and message handlers.
- Worker pools, streaming to Telegram, and membership verification.
</details>

---

<a name="dependencies"></a>
## 📦 Dependencies
- `aiogram>=3.0.0`
- `aiohttp>=3.8.0`
- `requests>=2.28.0`
- `websockets>=11.0.0`

---

<a name="contributing"></a>
## 🤝 Contributing
- Issues and pull requests are welcome.
- Do not commit tokens/keys into the repository.

---

<a name="license"></a>
## 📄 License
MIT — see [LICENSE](LICENSE)

---

## Programmed by Dezhcode
