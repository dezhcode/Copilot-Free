# Copilot Telegram Bot

<div align="center">

 یک ربات تلگرام هوشمند مبتنی بر Microsoft Copilot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot-Aiogram%203-blue?logo=telegram)](https://aiogram.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

</div>

## 📖 درباره پروژه

ربات تلگرام هوشمندی که از Microsoft Copilot برای تولید پاسخ‌های هوشمند استفاده می‌کند و برای هر تاپیک کانتکست جدا نگه می‌دارد. این ربات شامل ویژگی‌های مختلفی مثل پشتیبانی از زبان‌های مختلف، حالت پرایوت، و مدیریت کانتکست است.

## ✨ ویژگی‌ها

- 📝 **پاسخ‌دهی هوشمند** با استفاده از Microsoft Copilot
- 🌍 **پشتیبانی چندزبانه**: فارسی، انگلیسی، روسی، عربی
- 📂 **مدیریت کانتکست**: کانتکست جدا برای هر تاپیک
- 🎛️ **حالت‌های مختلف پاسخ**: کوتاه، نرمال، کامل، کد
- 🔒 **حالت پرایوت**: برای گفتگوهای حساس
- 📊 **آمار و تاریخچه**: مشاهده آمار و تاریخچه گفتگو
- ✅ **تایید عضویت**: در کانال برای دسترسی

## 💡 کاربردها

- 📚 آموزش و پاسخ به سوالات تحصیلی
- 💻 کمک برنامه‌نویسی و رفع اشکال کد
- 📝 خلاصه‌سازی و توضیح مطالب
- 🤝 مشاوره عمومی و پاسخ به سوالات روزمره
- 🌐 ترجمه و تبدیل متن‌ها

## 🚀 شروع سریع

### پیش‌نیازها

- Python 3.8 یا بالاتر
- توکن ربات تلگرام (از [@BotFather](https://t.me/BotFather))

### نصب و اجرا

1. کلون کردن ریپازیتوری:
```bash
git clone https://github.com/dezhcode/copilot-telegram-bot.git
cd copilot-telegram-bot
```

2. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

3. تنظیم متغیرهای محیطی:
   - `.env` فایل بسازید
   - توکن ربات خود را اضافه کنید:
   ```env
   BOT_TOKEN=your_bot_token_here
   USER_LLM_WORKERS=2
   NLP_LLM_WORKERS=1
   LLM_QUEUE_SIZE=200
   ```

4. اجرای ربات:
```bash
python main.py
```

## 📁 ساختار پروژه

```
v 1/
├── app/
│   ├── __init__.py
│   ├── bot.py          # منطق اصلی ربات و کنترل‌کننده‌ها
│   ├── config.py       # بارگذاری تنظیمات
│   ├── copilot_client.py  # کلاینت ارتباط با Copilot
│   ├── storage.py      # مدیریت دیتابیس SQLite
│   └── ui_texts.py     # متون رابط کاربری
├── main.py             # نقطه ورود
└── requirements.txt    # وابستگی‌ها
```

## 📦 وابستگی‌ها

- `aiogram>=3.0.0`: فریمورک ربات تلگرام
- `aiohttp>=3.8.0`: کلاینت HTTP ناهمزمان
- `requests>=2.28.0`: کلاینت HTTP همزمان
- `websockets>=11.0.0`: ارتباط WebSocket

## 📄 لایسنس

این پروژه تحت لایسنس MIT منتشر شده است. برای اطلاعات بیشتر فایل [LICENSE](LICENSE) را بخوانید.

## 🤝 مشارکت

مشارکت‌ها خوش آمدید! لطفاً یک issue بسازید یا یک pull request ارسال کنید.

## 👨‍💻 توسعه‌دهنده

- **Dezhcode** - [GitHub](https://github.com/dezhcode)

## Programmed by Dezhcode
