# Copilot Free

<div align="center">

<img src="image/Copilot-free.jpg" alt="Copilot Free Logo" width="220" />

**Copilot Free** — ربات تلگرام هوشمند مبتنی بر Microsoft Copilot  
[@CopilotFreeBot](https://t.me/CopilotFreeBot) • [Channel](https://t.me/Dezhcode)

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0)](https://aiogram.dev/)
[![Telegram](https://img.shields.io/badge/Telegram-@CopilotFreeBot-26A5E4?logo=telegram&logoColor=white)](https://t.me/CopilotFreeBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-2EA44F)](LICENSE)

</div>

زبان: **فارسی** • [English](README.md)

<a name="quick-start"></a>
## 🚀 شروع سریع
- نصب: `pip install -r requirements.txt`
- تنظیم توکن: `BOT_TOKEN=...`
- اجرا: `python main.py`

<a name="toc"></a>
## 🧭 فهرست
- [درباره](#about)
- [ویژگی‌ها](#features)
- [کاربردها](#use-cases)
- [نصب و اجرا](#install--run)
- [پیکربندی](#configuration)
- [دستورات ربات](#bot-commands)
- [نحوه کار](#how-it-works)
- [ساختار پروژه](#project-structure)
- [ماژول‌ها](#modules)
- [وابستگی‌ها](#dependencies)
- [مشارکت](#contributing)
- [لایسنس](#license)

---

<a name="about"></a>
## 📖 درباره
Copilot Free یک ربات تلگرام است که پاسخ‌ها را با Microsoft Copilot تولید می‌کند. ربات برای هر تاپیک/ترد یک **کانتکست جدا** نگه می‌دارد تا گفتگوها قاطی نشوند و پاسخ‌ها مرتبط‌تر باشند.

**لینک‌ها**
- ربات: [@CopilotFreeBot](https://t.me/CopilotFreeBot)
- کانال: [Dezhcode](https://t.me/Dezhcode)

---

<a name="features"></a>
## ✨ ویژگی‌ها
- چندزبانه: فارسی، انگلیسی، روسی، عربی
- کانتکست جدا برای هر تاپیک + ذخیره تاریخچه (SQLite)
- استریم پاسخ (آپدیت تدریجی پیام در تلگرام)
- حالت‌های پاسخ: کوتاه / نرمال / کامل / کد
- حالت Private برای گفتگوهای حساس (عدم ذخیره در DB و عدم استفاده از تاریخچه)
- ابزارهای مدیریت گفتگو (history/reset/stats)
- تایید عضویت در کانال

---

<a name="use-cases"></a>
## 💡 کاربردها
- پرسش و پاسخ عمومی و کمک روزمره
- کمک برنامه‌نویسی (دیباگ، توضیح کد، تولید نمونه‌کد)
- خلاصه‌سازی، بازنویسی و بهبود متن
- ترجمه و تمرین زبان

---

<a name="install--run"></a>
## 🧰 نصب و اجرا

### 1) دریافت پروژه
```bash
git clone <REPO_URL>
cd <REPO_DIR>
```

### 2) نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 3) تنظیم BOT_TOKEN و اجرا
این پروژه تنظیمات را از **متغیرهای محیطی** می‌خواند.

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

نکته: اگر از فایل `.env` استفاده می‌کنید، مطمئن شوید در محیط اجرا، متغیرها واقعاً Load می‌شوند (خود پروژه به‌تنهایی فایل `.env` را نمی‌خواند).

---

<a name="configuration"></a>
## ⚙️ پیکربندی

| متغیر | پیش‌فرض | توضیح |
|---|---:|---|
| `BOT_TOKEN` | — | توکن ربات تلگرام (ضروری) |
| `USER_LLM_WORKERS` | `2` | تعداد worker برای پیام‌های عادی کاربران |
| `NLP_LLM_WORKERS` | `1` | تعداد worker برای کارهای سنگین‌تر/اولویت‌دار |
| `LLM_QUEUE_SIZE` | `200` | ظرفیت صف درخواست‌ها |

---

<a name="bot-commands"></a>
## 🧾 دستورات ربات

| دستور | توضیح |
|---|---|
| `/start` | شروع و انتخاب زبان |
| `/help` | راهنما و منو |
| `/lang` | تغییر زبان |
| `/settings` | تنظیمات (حالت پاسخ، زمان، Private mode) |
| `/mode` | تغییر حالت پاسخ |
| `/history` | تاریخچه همین تاپیک |
| `/reset` | پاکسازی کانتکست همین تاپیک |
| `/reset_all` | پاکسازی همه تاپیک‌ها |
| `/stats` | آمار کاربر |
| `/about` | درباره ربات |

---

<a name="how-it-works"></a>
## 🔎 نحوه کار
نمای کلی جریان:
1. پیام کاربر دریافت می‌شود (اگر ریپلای باشد، متن پیام ریپلای‌شده هم اضافه می‌شود)
2. تاریخچه تاپیک از SQLite خوانده می‌شود (اگر Private mode خاموش باشد)
3. درخواست وارد صف می‌شود و با workerها پردازش می‌گردد
4. درخواست به Copilot ارسال می‌شود و پاسخ به صورت استریم برمی‌گردد
5. پیام در تلگرام آپدیت/ارسال می‌شود و در دیتابیس ذخیره می‌گردد (اگر Private mode خاموش باشد)

---

<a name="project-structure"></a>
## 📁 ساختار پروژه
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
├── README.md
└── README.fa.md
```

---

<a name="modules"></a>
## 🧩 ماژول‌ها

<details>
<summary><strong>main.py</strong> — نقطه ورود</summary>

- اجرای `run_bot()` و راه‌اندازی حلقه asyncio
</details>

<details>
<summary><strong>app/config.py</strong> — تنظیمات</summary>

- خواندن متغیرهای محیطی و اعمال حداقل‌های منطقی برای worker/queue
</details>

<details>
<summary><strong>app/copilot_client.py</strong> — ارتباط با Copilot</summary>

- شروع conversation و ارسال پیام از طریق WebSocket
- دریافت پاسخ به صورت استریم
</details>

<details>
<summary><strong>app/storage.py</strong> — دیتابیس SQLite</summary>

- ذخیره کاربران، پیام‌ها، تنظیمات تاپیک و خلاصه‌ها
- فراهم کردن تاریخچه برای ساخت prompt بهتر
</details>

<details>
<summary><strong>app/ui_texts.py</strong> — متن‌ها و کیبوردها</summary>

- متن‌های چندزبانه و ساخت inline keyboardها (زبان/عضویت/منو)
</details>

<details>
<summary><strong>app/bot.py</strong> — منطق ربات</summary>

- هندلرهای دستورات و پیام‌ها
- مدیریت صف/workerها و استریم پاسخ به کاربر
- بررسی عضویت در کانال
</details>

---

<a name="dependencies"></a>
## 📦 وابستگی‌ها
- `aiogram>=3.0.0`
- `aiohttp>=3.8.0`
- `requests>=2.28.0`
- `websockets>=11.0.0`

---

<a name="contributing"></a>
## 🤝 مشارکت
- Issue و Pull Request خوش آمدید.
- لطفاً توکن‌ها/کلیدها را داخل ریپو کامیت نکنید.

---

<a name="license"></a>
## 📄 لایسنس
MIT — فایل [LICENSE](LICENSE)

---

## Programmed by Dezhcode

