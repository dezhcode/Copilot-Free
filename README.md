# Copilot Free Telegram Bot

<div align="center">

<img src="image/Copilot-free.jpg" alt="Copilot Free Logo" width="220" />

**Copilot Free** — ربات تلگرام هوشمند مبتنی بر Microsoft Copilot  
[@CopilotFreeBot](https://t.me/CopilotFreeBot) • [Channel](https://t.me/Dezhcode)

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0)](https://aiogram.dev/)
[![Telegram](https://img.shields.io/badge/Telegram-@CopilotFreeBot-26A5E4?logo=telegram&logoColor=white)](https://t.me/CopilotFreeBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-2EA44F)](LICENSE)

</div>

## � شروع سریع
- نصب: `pip install -r requirements.txt`
- تنظیم توکن: `BOT_TOKEN=...`
- اجرا: `python main.py`

## 🧭 فهرست
- [درباره](#-درباره)
- [ویژگی‌ها](#-ویژگیها)
- [کاربردها](#-کاربردها)
- [نصب و اجرا](#-نصب-و-اجرا)
- [پیکربندی](#-پیکربندی)
- [دستورات ربات](#-دستورات-ربات)
- [نحوه کار](#-نحوه-کار)
- [ساختار پروژه](#-ساختار-پروژه)
- [ماژول‌ها](#-ماژولها)
- [وابستگی‌ها](#-وابستگیها)
- [مشارکت](#-مشارکت)
- [لایسنس](#-لایسنس)

---

## 📖 درباره
Copilot Free یک ربات تلگرام است که پاسخ‌ها را با Microsoft Copilot تولید می‌کند. ربات برای هر تاپیک (Topic/Thread) کانتکست جدا نگه می‌دارد تا گفتگوها قاطی نشوند و پاسخ‌ها مرتبط‌تر باشند.

**لینک‌های مهم**
- ربات: [@CopilotFreeBot](https://t.me/CopilotFreeBot)
- کانال: [Dezhcode](https://t.me/Dezhcode)

---

## ✨ ویژگی‌ها
- چندزبانه: فارسی، انگلیسی، روسی، عربی
- مدیریت کانتکست جدا برای هر تاپیک + تاریخچه
- استریم پاسخ (نمایش تدریجی پاسخ در تلگرام)
- حالت‌های پاسخ: کوتاه / نرمال / کامل / کد
- حالت Private برای گفتگوهای حساس (عدم ذخیره‌سازی در DB)
- آمار و ابزارهای مدیریت گفتگو (history/reset/stats)
- سیستم تایید عضویت در کانال

---

## 💡 کاربردها
- پاسخ به سوالات عمومی و روزمره
- کمک برنامه‌نویسی (اشکال‌زدایی، توضیح کد، تولید نمونه کد)
- خلاصه‌سازی، بازنویسی و بهبود متن
- ترجمه و تمرین زبان

---

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

### 3) تنظیم BOT_TOKEN
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

## ⚙️ پیکربندی

| متغیر | پیش‌فرض | توضیح |
|------|---------|------|
| `BOT_TOKEN` | — | توکن ربات تلگرام (ضروری) |
| `USER_LLM_WORKERS` | `2` | تعداد worker برای پیام‌های عادی کاربران |
| `NLP_LLM_WORKERS` | `1` | تعداد worker برای کارهای سنگین‌تر/اولویت‌دار |
| `LLM_QUEUE_SIZE` | `200` | ظرفیت صف درخواست‌ها |

---

## 🧾 دستورات ربات

| دستور | توضیح |
|------|------|
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

## 🔎 نحوه کار
جریان کلی پاسخ‌دهی به این شکل است:
1. پیام کاربر دریافت می‌شود (در صورت Reply شدن، متن پیام ریپلای‌شده هم وارد کانتکست می‌شود)
2. کانتکست/تاریخچه مربوط به تاپیک از SQLite خوانده می‌شود (اگر Private mode خاموش باشد)
3. درخواست وارد صف می‌شود و توسط workerها پردازش می‌گردد
4. درخواست به Copilot ارسال می‌شود و پاسخ به صورت استریم برمی‌گردد
5. پاسخ به تلگرام ارسال/آپدیت می‌شود و در دیتابیس ذخیره می‌گردد (اگر Private mode خاموش باشد)

---

## 📁 ساختار پروژه
```
v 1/
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

## 🧩 ماژول‌ها

<details>
<summary><strong>main.py</strong> — نقطه ورود</summary>

- اجرای `run_bot()` و راه‌اندازی حلقه asyncio
</details>

<details>
<summary><strong>app/config.py</strong> — خواندن تنظیمات</summary>

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

## 📦 وابستگی‌ها
- `aiogram>=3.0.0`
- `aiohttp>=3.8.0`
- `requests>=2.28.0`
- `websockets>=11.0.0`

---

## 🤝 مشارکت
- Issue و Pull Request خوش‌آمدید.
- لطفاً توکن‌ها/کلیدها را داخل ریپو کامیت نکنید.

---

## 📄 لایسنس
MIT — فایل [LICENSE](LICENSE)

---

## Programmed by Dezhcode
