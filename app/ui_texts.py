from typing import Any, Dict, Optional

CHANNEL_USERNAME = "@Dezhcode"
CHANNEL_URL = "https://t.me/Dezhcode"

SUPPORTED_LANGS: Dict[str, str] = {
    "fa": "🇮🇷 فارسی",
    "en": "🇺🇸 English",
    "ru": "🇷🇺 Русский",
    "ar": "🇸🇦 العربية",
}

TEXTS: Dict[str, Dict[str, str]] = {
    "choose_language": {
        "fa": "🌍 زبان رو انتخاب کن\n\nبعدش از منوی پایین (≡) میتونی راهنما رو ببینی",
        "en": "🌍 Choose a language\n\nThen use the menu (≡) to open Help",
        "ru": "🌍 Выберите язык\n\nЗатем откройте меню (≡) и выберите Help",
        "ar": "🌍 اختر اللغة\n\nثم افتح القائمة (≡) واختر Help",
    },
    "start_welcome": {
        "fa": "👋 خوش اومدی\n\n👥 کاربران ربات: {users}\n💬 چت های ربات: {chats}\n\nبرای شروع فقط زبان رو انتخاب کن",
        "en": "👋 Welcome\n\n👥 Bot users: {users}\n💬 Bot chats: {chats}\n\nTo start, choose your language",
        "ru": "👋 Добро пожаловать\n\n👥 Пользователей: {users}\n💬 Чатов: {chats}\n\nДля начала выберите язык",
        "ar": "👋 أهلاً بك\n\n👥 مستخدمون: {users}\n💬 دردشات: {chats}\n\nللبدء اختر لغتك",
    },
    "help_text": {
        "fa": (
            "🧭 راهنمای سریع\n\n"
            "از منوی پایین (≡) هم میتونی همین گزینه ها رو انتخاب کنی\n\n"
            "🧩 عمومی\n"
            "• /help راهنما و منو\n"
            "• /lang تغییر زبان\n"
            "• /settings تنظیمات\n"
            "• /about درباره ربات\n\n"
            "🎛 پاسخ دهی\n"
            "• /mode انتخاب حالت پاسخ\n\n"
            "🧾 گفتگو\n"
            "• /history تاریخچه همین تاپیک\n"
            "• /reset پاکسازی کانتکست همین تاپیک\n"
            "• /reset_all پاکسازی همه تاپیک ها\n"
            "• /stats آمار شما\n\n"
            "نکته\n"
            "اگر روی یک پیام ریپلای کنی همان پیام هم وارد کانتکست میشه"
        ),
        "en": (
            "🧭 Quick help\n\n"
            "You can also use the bottom menu (≡) to open the same sections\n\n"
            "🧩 General\n"
            "• /help help & menu\n"
            "• /lang change language\n"
            "• /settings settings\n"
            "• /about about the bot\n\n"
            "🎛 Reply mode\n"
            "• /mode choose reply mode\n\n"
            "🧾 Chat\n"
            "• /history this topic history\n"
            "• /reset clear this topic context\n"
            "• /reset_all clear all topics\n"
            "• /stats your stats\n\n"
            "Tip\n"
            "If you reply to a message, the bot will include it in context"
        ),
        "ru": (
            "🧭 Быстрая справка\n\n"
            "Можно использовать нижнее меню (≡) для открытия этих разделов\n\n"
            "🧩 Общее\n"
            "• /help справка и меню\n"
            "• /lang сменить язык\n"
            "• /settings настройки\n"
            "• /about о боте\n\n"
            "🎛 Режим ответа\n"
            "• /mode выбрать режим\n\n"
            "🧾 Чат\n"
            "• /history история текущей темы\n"
            "• /reset очистить контекст этой темы\n"
            "• /reset_all очистить все темы\n"
            "• /stats статистика\n\n"
            "Совет\n"
            "Если ответить на сообщение, бот учтёт его в контексте"
        ),
        "ar": (
            "🧭 مساعدة سريعة\n\n"
            "يمكنك أيضًا استخدام القائمة السفلية (≡) لفتح نفس الأقسام\n\n"
            "🧩 عام\n"
            "• /help المساعدة والقائمة\n"
            "• /lang تغيير اللغة\n"
            "• /settings الإعدادات\n"
            "• /about حول البوت\n\n"
            "🎛 نمط الرد\n"
            "• /mode اختيار نمط الرد\n\n"
            "🧾 المحادثة\n"
            "• /history سجل هذا الموضوع\n"
            "• /reset مسح سياق هذا الموضوع\n"
            "• /reset_all مسح كل المواضيع\n"
            "• /stats إحصاءاتك\n\n"
            "ملاحظة\n"
            "إذا رددت على رسالة، سيأخذها البوت ضمن السياق"
        ),
    },
    "about_text": {
        "fa": "ℹ️ درباره ربات\n\nاین ربات پاسخ ها رو با Copilot تولید میکنه و برای هر تاپیک کانتکست جدا نگه میداره\nبرای بهترین نتیجه سوالت رو دقیق بپرس و اگر لازم بود روی پیام قبلی ریپلای کن",
        "en": "ℹ️ About\n\nThis bot uses Copilot to generate answers and keeps a separate context per topic.\nFor best results, be specific and reply to a message when needed.",
        "ru": "ℹ️ О боте\n\nБот использует Copilot для ответов и хранит отдельный контекст для каждой темы.\nДля лучшего результата задавайте вопрос точнее и при необходимости отвечайте на сообщение.",
        "ar": "ℹ️ حول البوت\n\nيستخدم هذا البوت Copilot لتوليد الإجابات ويحافظ على سياق منفصل لكل موضوع.\nلأفضل نتيجة، كن محددًا وردّ على الرسالة عند الحاجة.",
    },
    "settings_text": {
        "fa": "⚙️ تنظیمات\n\nحالت پاسخ و نمایش زمان رو از همینجا مدیریت کن",
        "en": "⚙️ Settings\n\nManage reply mode and duration display here",
        "ru": "⚙️ Настройки\n\nЗдесь можно выбрать режим ответа и показ времени",
        "ar": "⚙️ الإعدادات\n\nقم بإدارة نمط الرد وعرض الوقت هنا",
    },
    "saved": {
        "fa": "✅ ذخیره شد",
        "en": "✅ Saved",
        "ru": "✅ Сохранено",
        "ar": "✅ تم الحفظ",
    },
    "mode_set": {
        "fa": "✅ حالت پاسخ تنظیم شد\n\nحالت فعلی: {mode}",
        "en": "✅ Reply mode updated\n\nCurrent mode: {mode}",
        "ru": "✅ Режим ответа обновлён\n\nТекущий режим: {mode}",
        "ar": "✅ تم تحديث نمط الرد\n\nالنمط الحالي: {mode}",
    },
    "history_empty": {
        "fa": "🧾 این تاپیک هنوز چیزی برای نمایش نداره",
        "en": "🧾 Nothing to show in this topic yet",
        "ru": "🧾 В этой теме пока нечего показать",
        "ar": "🧾 لا يوجد شيء لعرضه في هذا الموضوع بعد",
    },
    "history_title": {
        "fa": "🧾 تاریخچه همین تاپیک",
        "en": "🧾 Topic history",
        "ru": "🧾 История темы",
        "ar": "🧾 سجل الموضوع",
    },
    "history_subtitle": {
        "fa": "آخرین پیام ها",
        "en": "Latest messages",
        "ru": "Последние сообщения",
        "ar": "أحدث الرسائل",
    },
    "reset_thread_prompt": {
        "fa": "🧹 پاکسازی کانتکست همین تاپیک\n\nبا تایید کردن تاریخچه همین تاپیک پاک میشه",
        "en": "🧹 Clear this topic\n\nConfirm to clear this topic history and context",
        "ru": "🧹 Очистить эту тему\n\nПодтвердите, чтобы очистить историю и контекст этой темы",
        "ar": "🧹 مسح هذا الموضوع\n\nأكّد لمسح سجل وسياق هذا الموضوع",
    },
    "reset_all_prompt": {
        "fa": "🧨 پاکسازی همه تاپیک ها\n\nبا تایید کردن کل تاریخچه شما در این چت پاک میشه",
        "en": "🧨 Clear all topics\n\nConfirm to clear all your history in this chat",
        "ru": "🧨 Очистить все темы\n\nПодтвердите, чтобы очистить всю вашу историю в этом чате",
        "ar": "🧨 مسح كل المواضيع\n\nأكّد لمسح كل سجلّك في هذه الدردشة",
    },
    "confirm_final": {
        "fa": "⚠️ تایید نهایی\n\nاگر مطمئنی انجام بده",
        "en": "⚠️ Final confirmation\n\nProceed only if you're sure",
        "ru": "⚠️ Финальное подтверждение\n\nПродолжайте только если уверены",
        "ar": "⚠️ تأكيد نهائي\n\nتابع فقط إذا كنت متأكدًا",
    },
    "done_reset_thread": {
        "fa": "✅ انجام شد\n\n{count} پیام از همین تاپیک پاک شد",
        "en": "✅ Done\n\nCleared {count} messages from this topic",
        "ru": "✅ Готово\n\nУдалено {count} сообщений в этой теме",
        "ar": "✅ تم\n\nتم حذف {count} رسالة من هذا الموضوع",
    },
    "done_reset_all": {
        "fa": "✅ انجام شد\n\n{count} پیام از همه تاپیک ها پاک شد",
        "en": "✅ Done\n\nCleared {count} messages from all topics",
        "ru": "✅ Готово\n\nУдалено {count} сообщений из всех тем",
        "ar": "✅ تم\n\nتم حذف {count} رسالة من كل المواضيع",
    },
    "stats_title": {
        "fa": "📊 آمار شما",
        "en": "📊 Your stats",
        "ru": "📊 Ваша статистика",
        "ar": "📊 إحصاءاتك",
    },
    "stats_messages": {
        "fa": "🧾 پیام های ذخیره شده: {count}",
        "en": "🧾 Saved messages: {count}",
        "ru": "🧾 Сохранённые сообщения: {count}",
        "ar": "🧾 الرسائل المحفوظة: {count}",
    },
    "stats_duration": {
        "fa": "⏱ نمایش زمان: {value}",
        "en": "⏱ Duration display: {value}",
        "ru": "⏱ Показ времени: {value}",
        "ar": "⏱ عرض الوقت: {value}",
    },
    "stats_mode": {
        "fa": "🎛 حالت پاسخ: {value}",
        "en": "🎛 Reply mode: {value}",
        "ru": "🎛 Режим ответа: {value}",
        "ar": "🎛 نمط الرد: {value}",
    },
    "menu_settings": {"fa": "⚙️ تنظیمات", "en": "⚙️ Settings", "ru": "⚙️ Настройки", "ar": "⚙️ الإعدادات"},
    "menu_lang": {"fa": "🌍 زبان", "en": "🌍 Language", "ru": "🌍 Язык", "ar": "🌍 اللغة"},
    "menu_history": {"fa": "🧾 تاریخچه", "en": "🧾 History", "ru": "🧾 История", "ar": "🧾 السجل"},
    "menu_stats": {"fa": "📊 آمار", "en": "📊 Stats", "ru": "📊 Статистика", "ar": "📊 إحصاءات"},
    "menu_about": {"fa": "ℹ️ درباره", "en": "ℹ️ About", "ru": "ℹ️ О боте", "ar": "ℹ️ حول"},
    "menu_help": {"fa": "🆘 راهنما", "en": "🆘 Help", "ru": "🆘 Помощь", "ar": "🆘 مساعدة"},
    "menu_channel": {"fa": "📢 کانال", "en": "📢 Channel", "ru": "📢 Канал", "ar": "📢 القناة"},
    "menu_profile": {"fa": "👤 پروفایل", "en": "👤 Profile", "ru": "👤 Профиль", "ar": "👤 الملف الشخصي"},
    "btn_confirm": {"fa": "✅ انجام بده", "en": "✅ Confirm", "ru": "✅ Подтвердить", "ar": "✅ تأكيد"},
    "btn_cancel": {"fa": "لغو", "en": "Cancel", "ru": "Отмена", "ar": "إلغاء"},
    "btn_reset_thread": {"fa": "🧹 ریست همین تاپیک", "en": "🧹 Reset topic", "ru": "🧹 Сброс темы", "ar": "🧹 إعادة ضبط الموضوع"},
    "btn_reset_all": {"fa": "🧨 ریست همه تاپیک‌ها", "en": "🧨 Reset all", "ru": "🧨 Сбросить всё", "ar": "🧨 إعادة ضبط الكل"},
    "on": {"fa": "روشن", "en": "on", "ru": "вкл", "ar": "تشغيل"},
    "off": {"fa": "خاموش", "en": "off", "ru": "выкл", "ar": "إيقاف"},
    "dur_on": {"fa": "⏱ زمان: روشن", "en": "⏱ Time: on", "ru": "⏱ Время: вкл", "ar": "⏱ الوقت: تشغيل"},
    "dur_off": {"fa": "⏱ زمان: خاموش", "en": "⏱ Time: off", "ru": "⏱ Время: выкл", "ar": "⏱ الوقت: إيقاف"},
    "mode_label_short": {"fa": "⚡ حالت: کوتاه", "en": "⚡ Mode: short", "ru": "⚡ Режим: коротко", "ar": "⚡ النمط: قصير"},
    "mode_label_normal": {"fa": "🧠 حالت: نرمال", "en": "🧠 Mode: normal", "ru": "🧠 Режим: обычный", "ar": "🧠 النمط: عادي"},
    "mode_label_detailed": {"fa": "📚 حالت: کامل", "en": "📚 Mode: detailed", "ru": "📚 Режим: подробно", "ar": "📚 النمط: مفصل"},
    "mode_label_code": {"fa": "💻 حالت: کد", "en": "💻 Mode: code", "ru": "💻 Режим: код", "ar": "💻 النمط: كود"},
    "mode_short": {"fa": "⚡ کوتاه", "en": "⚡ Short", "ru": "⚡ Коротко", "ar": "⚡ قصير"},
    "mode_normal": {"fa": "🧠 نرمال", "en": "🧠 Normal", "ru": "🧠 Обычный", "ar": "🧠 عادي"},
    "mode_detailed": {"fa": "📚 کامل", "en": "📚 Detailed", "ru": "📚 Подробно", "ar": "📚 مفصل"},
    "mode_code": {"fa": "💻 کد", "en": "💻 Code", "ru": "💻 Код", "ar": "💻 كود"},
    "private_prompt": {
        "fa": "🔒 پرایوت مود این تاپیک؟\n\nاگر فعالش کنی:\n• پیام ها و پاسخ ها داخل دیتابیس ذخیره نمیشن\n• تاریخچه این تاپیک برای ادامه گفتگو استفاده نمیشه\n\nاین گزینه برای گفتگوهای حساس یا یکبارمصرف خوبه",
        "en": "🔒 Private mode for this topic?\n\nIf enabled:\n• Messages and answers are not saved\n• This topic history won't be used for context\n\nGreat for sensitive or one-off chats",
        "ru": "🔒 Приватный режим для этой темы?\n\nЕсли включить:\n• Сообщения и ответы не сохраняются\n• История темы не используется как контекст\n\nПодходит для чувствительных или разовых чатов",
        "ar": "🔒 وضع خاص لهذا الموضوع؟\n\nعند التفعيل:\n• لا يتم حفظ الرسائل والردود\n• لن يُستخدم سجل هذا الموضوع كسياق\n\nمناسب للمحادثات الحساسة أو المؤقتة",
    },
    "btn_private_on": {"fa": "✅ فعالش کن", "en": "✅ Enable", "ru": "✅ Включить", "ar": "✅ تفعيل"},
    "btn_private_off": {"fa": "❌ لازم نیست", "en": "❌ Not now", "ru": "❌ Не нужно", "ar": "❌ لا"},
    "private_on": {"fa": "🔒 پرایوت: روشن", "en": "🔒 Private: on", "ru": "🔒 Приват: вкл", "ar": "🔒 خاص: تشغيل"},
    "private_off": {"fa": "🔓 پرایوت: خاموش", "en": "🔓 Private: off", "ru": "🔓 Приват: выкл", "ar": "🔓 خاص: إيقاف"},
    "profile_title": {"fa": "👤 پروفایل شما", "en": "👤 Your profile", "ru": "👤 Ваш профиль", "ar": "👤 ملفك الشخصي"},
    "profile_empty": {
        "fa": "هنوز چیزی اینجا ذخیره نشده\n\nهر وقت اطلاعات غیر حساس از حرفات برداشت کنم اینجا میاد",
        "en": "Nothing saved yet\n\nWhen I detect non-sensitive facts, they'll appear here",
        "ru": "Пока ничего не сохранено\n\nКогда будут найденые факты (без чувствительных данных), они появятся здесь",
        "ar": "لا يوجد شيء محفوظ بعد\n\nعند اكتشاف معلومات غير حساسة ستظهر هنا",
    },
    "btn_profile_clear": {"fa": "🗑 پاکسازی پروفایل", "en": "🗑 Clear profile", "ru": "🗑 Очистить", "ar": "🗑 مسح"},
    "btn_refresh": {"fa": "↻ بروزرسانی", "en": "↻ Refresh", "ru": "↻ Обновить", "ar": "↻ تحديث"},
    "btn_prev": {"fa": "⬅️ جدیدتر", "en": "⬅️ Newer", "ru": "⬅️ Новее", "ar": "⬅️ أحدث"},
    "btn_next": {"fa": "قدیمی‌تر ➡️", "en": "Older ➡️", "ru": "Старее ➡️", "ar": "أقدم ➡️"},
    "profile_cleared": {"fa": "✅ پروفایل پاک شد", "en": "✅ Profile cleared", "ru": "✅ Профиль очищен", "ar": "✅ تم المسح"},
    "join_required": {
        "fa": "🔒 برای ادامه باید عضو کانال بشی\nبعدش روی تایید عضویت بزن",
        "en": "🔒 Membership required to continue\nThen tap the verify button",
        "ru": "🔒 Для продолжения нужно подписаться\nЗатем нажмите кнопку подтверждения",
        "ar": "🔒 يجب الاشتراك للمتابعة\nثم اضغط زر التحقق",
    },
    "verify_failed": {
        "fa": "هنوز عضو کانال نیستی\nعضو شو و دوباره تایید کن",
        "en": "You are not a member yet\nJoin and try again",
        "ru": "Вы ещё не подписаны\nПодпишитесь и попробуйте снова",
        "ar": "أنت لست مشتركًا بعد\nانضم ثم حاول مرة أخرى",
    },
    "verified": {
        "fa": "✅ عضویت تایید شد",
        "en": "✅ Verified",
        "ru": "✅ Подтверждено",
        "ar": "✅ تم التأكيد",
    },
    "send_prompt": {
        "fa": "حالا سوالت رو بپرس",
        "en": "Send a message",
        "ru": "Отправьте сообщение",
        "ar": "أرسل رسالة",
    },
    "thinking": {
        "fa": "🧠 دارم فکر میکنم",
        "en": "🧠 Thinking",
        "ru": "🧠 Думаю",
        "ar": "🧠 أفكر",
    },
    "error_ai": {
        "fa": "❌ اتصال به Copilot مشکل داشت\nدوباره تلاش کن",
        "en": "❌ Error connecting to Copilot",
        "ru": "❌ Ошибка подключения к Copilot",
        "ar": "❌ خطأ في الاتصال بـ Copilot",
    },
    "error_membership": {
        "fa": "❌ بررسی عضویت انجام نشد\nربات باید داخل کانال ادمین باشد",
        "en": "❌ Failed to check membership\nBot must be admin in the channel",
        "ru": "❌ Не удалось проверить подписку\nБот должен быть админом в канале",
        "ar": "❌ تعذر التحقق من الاشتراك\nيجب أن يكون البوت مشرفًا في القناة",
    },
    "btn_summarize": {
        "fa": "📝 خلاصه",
        "en": "📝 Summarize",
        "ru": "📝 Сжато",
        "ar": "📝 لخّص",
    },
    "btn_explain": {
        "fa": "➕ بیشتر بگو",
        "en": "➕ Explain more",
        "ru": "➕ Подробнее",
        "ar": "➕ اشرح أكثر",
    },
}


def t(lang: str, key: str) -> str:
    lang = (lang or "").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    return TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get("en") or key


def _btn(text: str, *, callback_data: Optional[str] = None, url: Optional[str] = None, style: Optional[str] = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"text": text}
    if callback_data is not None:
        data["callback_data"] = callback_data
    if url is not None:
        data["url"] = url
    if style is not None:
        data["style"] = style
    return data


def kb_language(current_lang: Optional[str] = None) -> Dict[str, Any]:
    current_lang = (current_lang or "").strip().lower()
    def st(code: str) -> str:
        return "success" if code == current_lang else "danger"
    return {
        "inline_keyboard": [
            [
                _btn(SUPPORTED_LANGS["en"], callback_data="lang:en", style=st("en")),
                _btn(SUPPORTED_LANGS["fa"], callback_data="lang:fa", style=st("fa")),
            ],
            [
                _btn(SUPPORTED_LANGS["ru"], callback_data="lang:ru", style=st("ru")),
                _btn(SUPPORTED_LANGS["ar"], callback_data="lang:ar", style=st("ar")),
            ],
        ]
    }


def kb_join(lang: str) -> Dict[str, Any]:
    join_label = {
        "fa": "📢 عضویت در کانال",
        "en": "📢 Join channel",
        "ru": "📢 Подписаться",
        "ar": "📢 انضم للقناة",
    }.get(lang, "📢 Join channel")
    verify_label = {
        "fa": "✅ تایید عضویت",
        "en": "✅ I joined",
        "ru": "✅ Я подписался",
        "ar": "✅ تحقق",
    }.get(lang, "✅ I joined")

    return {
        "inline_keyboard": [
            [_btn(join_label, url=CHANNEL_URL, style="primary")],
            [_btn(verify_label, callback_data="verify", style="success")],
        ]
    }
