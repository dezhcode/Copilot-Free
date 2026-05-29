import asyncio
import os
import time
from dataclasses import dataclass
from secrets import randbelow
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

import aiohttp

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, BotCommandScopeChatMember, CallbackQuery, Message

from app.config import load_config
from app.copilot_client import CopilotClient
from app.ui_texts import CHANNEL_URL, CHANNEL_USERNAME, SUPPORTED_LANGS, kb_join, kb_language, t
from app.storage import Storage, StoredMessage

COMMANDS_BY_LANG: Dict[str, List[BotCommand]] = {
    "en": [
        BotCommand(command="start", description="🚀 Start"),
        BotCommand(command="help", description="🧭 Help & menu"),
        BotCommand(command="lang", description="🌍 Language"),
        BotCommand(command="settings", description="⚙️ Settings"),
        BotCommand(command="profile", description="👤 Profile"),
        BotCommand(command="mode", description="🎛 Reply mode"),
        BotCommand(command="history", description="🧾 Topic history"),
        BotCommand(command="reset", description="🧹 Reset topic"),
        BotCommand(command="reset_all", description="🧨 Reset all"),
        BotCommand(command="stats", description="📊 Stats"),
        BotCommand(command="about", description="ℹ️ About"),
    ],
    "fa": [
        BotCommand(command="start", description="🚀 شروع"),
        BotCommand(command="help", description="🧭 راهنما و منو"),
        BotCommand(command="lang", description="🌍 زبان"),
        BotCommand(command="settings", description="⚙️ تنظیمات"),
        BotCommand(command="profile", description="👤 پروفایل"),
        BotCommand(command="mode", description="🎛 حالت پاسخ"),
        BotCommand(command="history", description="🧾 تاریخچه تاپیک"),
        BotCommand(command="reset", description="🧹 ریست تاپیک"),
        BotCommand(command="reset_all", description="🧨 ریست همه"),
        BotCommand(command="stats", description="📊 آمار"),
        BotCommand(command="about", description="ℹ️ درباره"),
    ],
    "ru": [
        BotCommand(command="start", description="🚀 Старт"),
        BotCommand(command="help", description="🧭 Помощь и меню"),
        BotCommand(command="lang", description="🌍 Язык"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="mode", description="🎛 Режим ответа"),
        BotCommand(command="history", description="🧾 История темы"),
        BotCommand(command="reset", description="🧹 Сброс темы"),
        BotCommand(command="reset_all", description="🧨 Сбросить всё"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="about", description="ℹ️ О боте"),
    ],
    "ar": [
        BotCommand(command="start", description="🚀 بدء"),
        BotCommand(command="help", description="🧭 مساعدة وقائمة"),
        BotCommand(command="lang", description="🌍 اللغة"),
        BotCommand(command="settings", description="⚙️ الإعدادات"),
        BotCommand(command="profile", description="👤 الملف الشخصي"),
        BotCommand(command="mode", description="🎛 نمط الرد"),
        BotCommand(command="history", description="🧾 سجل الموضوع"),
        BotCommand(command="reset", description="🧹 إعادة ضبط الموضوع"),
        BotCommand(command="reset_all", description="🧨 إعادة ضبط الكل"),
        BotCommand(command="stats", description="📊 إحصاءات"),
        BotCommand(command="about", description="ℹ️ حول"),
    ],
}


@dataclass(frozen=True)
class _StreamWorkItem:
    stream_factory: Callable[[], AsyncIterator[str]]
    out_queue: "asyncio.Queue[Optional[str]]"
    done: "asyncio.Future[None]"


class _StreamWorkerPool:
    def __init__(self, *, workers: int, max_queue_size: int) -> None:
        self._queue: "asyncio.Queue[_StreamWorkItem]" = asyncio.Queue(maxsize=max(1, int(max_queue_size)))
        self._tasks: List["asyncio.Task[None]"] = []
        self._workers = max(1, int(workers))

    def start(self) -> None:
        if self._tasks:
            return
        for _ in range(self._workers):
            self._tasks.append(asyncio.create_task(self._worker()))

    async def aclose(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _worker(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                async for delta in item.stream_factory():
                    await item.out_queue.put(delta)
                if not item.done.done():
                    item.done.set_result(None)
            except Exception as e:
                if not item.done.done():
                    item.done.set_exception(e)
            finally:
                try:
                    await item.out_queue.put(None)
                except Exception:
                    pass
                self._queue.task_done()

    async def stream(self, stream_factory: Callable[[], AsyncIterator[str]]) -> AsyncIterator[str]:
        out_q: "asyncio.Queue[Optional[str]]" = asyncio.Queue(maxsize=128)
        loop = asyncio.get_running_loop()
        done: "asyncio.Future[None]" = loop.create_future()
        await self._queue.put(_StreamWorkItem(stream_factory=stream_factory, out_queue=out_q, done=done))
        try:
            while True:
                chunk = await out_q.get()
                if chunk is None:
                    break
                yield chunk
            await done
        finally:
            if not done.done():
                done.cancel()


class QueuedCopilotClient:
    def __init__(self, inner: CopilotClient, *, user_pool: _StreamWorkerPool, nlp_pool: _StreamWorkerPool) -> None:
        self._inner = inner
        self._user_pool = user_pool
        self._nlp_pool = nlp_pool

    async def ask(self, user_text: str, language: str = "en", priority: int = 0) -> str:
        out = ""
        async for delta in self.ask_stream(user_text, language=language, priority=priority):
            out += delta
        return out.strip() or " "

    async def ask_stream(self, user_text: str, language: str = "en", priority: int = 0) -> AsyncIterator[str]:
        pool = self._user_pool if int(priority) <= 0 else self._nlp_pool

        async def _src() -> AsyncIterator[str]:
            async for d in self._inner.ask_stream(user_text, language=language):
                yield d

        async for delta in pool.stream(_src):
            yield delta



async def _set_commands_for_user(bot: Bot, *, chat_id: int, user_id: int, lang: str) -> None:
    lang = (lang or "").strip().lower()
    cmds = COMMANDS_BY_LANG.get(lang) or COMMANDS_BY_LANG["en"]
    scope = BotCommandScopeChatMember(chat_id=chat_id, user_id=user_id)
    try:
        await bot.set_my_commands(cmds, scope=scope)
    except Exception:
        return


def _split_telegram_text(text: str, chunk_size: int = 4000) -> List[str]:
    text = text or " "
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _get_thread_id(message: Message) -> Optional[int]:
    return getattr(message, "message_thread_id", None)


def _new_draft_id() -> int:
    return randbelow(2_000_000_000) + 1


def _get_bot_token(bot: Bot) -> str:
    token = getattr(bot, "token", None) or getattr(bot, "_token", None)
    if not token:
        raise RuntimeError("Bot token not found")
    return str(token)


def _get_aiohttp_session(bot: Bot) -> Optional[aiohttp.ClientSession]:
    session = getattr(getattr(bot, "session", None), "session", None) or getattr(getattr(bot, "session", None), "_session", None)
    if isinstance(session, aiohttp.ClientSession):
        return session
    return None


def _contains_style(value: Any) -> bool:
    if isinstance(value, dict):
        if "style" in value:
            return True
        return any(_contains_style(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_style(v) for v in value)
    return False


def _strip_style(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if k == "style":
                continue
            out[k] = _strip_style(v)
        return out
    if isinstance(value, list):
        return [_strip_style(v) for v in value]
    return value


def _sanitize_markdown_v2(text: str) -> str:
    raw = (text or " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("- "):
            lines[i] = "• " + line[2:]
    raw = "\n".join(lines)
    specials = set("\\~>#+-=|{}.!-")
    out: List[str] = []
    for ch in raw:
        if ch in specials:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _shorten(text: str, limit: int = 600) -> str:
    s = (text or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    s = " ".join(s.split())
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"


def _topic_name(message_thread_id: Optional[int]) -> str:
    if message_thread_id is None:
        return "General"
    return f"Topic {message_thread_id}"


def _build_history_block(*, current_thread_id: Optional[int], messages: List[StoredMessage]) -> str:
    current: List[StoredMessage] = []
    other: Dict[Optional[int], List[StoredMessage]] = {}
    for m in messages:
        if m.role == "user" and m.text in {"[summarize]", "[explain_more]"}:
            continue
        if m.message_thread_id == current_thread_id:
            current.append(m)
        else:
            other.setdefault(m.message_thread_id, []).append(m)

    blocks: List[str] = []
    if current:
        blocks.append(f"[{_topic_name(current_thread_id)}]")
        for m in current[-12:]:
            prefix = "U" if m.role == "user" else "A"
            blocks.append(f"{prefix}: {_shorten(m.text)}")

    for tid, items in sorted(other.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
        if not items:
            continue
        blocks.append(f"[{_topic_name(tid)}]")
        for m in items[-6:]:
            prefix = "U" if m.role == "user" else "A"
            blocks.append(f"{prefix}: {_shorten(m.text)}")

    return "\n".join(blocks).strip()


async def _compose_prompt(
    *,
    storage: Storage,
    user_id: int,
    chat_id: int,
    current_thread_id: Optional[int],
    response_mode: str,
    private_mode: bool,
    user_text: str,
    reply_to_telegram_message_id: Optional[int],
    reply_fallback_text: str,
) -> str:
    history_msgs: List[StoredMessage] = []
    if not private_mode:
        history_msgs = await storage.get_recent_messages(user_id=user_id, chat_id=chat_id, message_thread_id=current_thread_id, limit=80)
    history_block = _build_history_block(current_thread_id=current_thread_id, messages=history_msgs) if history_msgs else ""
    parts: List[str] = []
    if history_block:
        parts.append("Conversation history (grouped by topic):\n" + history_block)
    if not private_mode:
        facts = await storage.list_profile_facts(user_id=user_id, limit=8)
        if facts:
            parts.append("User profile facts:\n" + "\n".join(f"- {f}" for f in facts))
        topic_summary = await storage.get_topic_summary(user_id=user_id, chat_id=chat_id, message_thread_id=current_thread_id)
        if topic_summary:
            parts.append("Topic summary:\n" + topic_summary)
    if reply_to_telegram_message_id is not None:
        if not private_mode:
            replied = await storage.get_message_by_telegram_id(chat_id=chat_id, telegram_message_id=reply_to_telegram_message_id)
            if replied and replied.text.strip():
                parts.append(f"User replied to this {replied.role} message:\n{replied.text.strip()}")
            elif reply_fallback_text.strip():
                parts.append("User replied to this message:\n" + reply_fallback_text.strip())
        elif reply_fallback_text.strip():
            parts.append("User replied to this message:\n" + reply_fallback_text.strip())
    elif reply_fallback_text.strip():
        parts.append("User replied to this message:\n" + reply_fallback_text.strip())
    mode = (response_mode or "normal").strip().lower()
    mode_hint = {
        "short": "Write a short, concise answer.",
        "normal": "",
        "detailed": "Write a detailed, thorough answer.",
        "code": "Prefer code and actionable steps when relevant. Use code blocks when useful.",
    }.get(mode, "")
    if mode_hint:
        parts.append("Answer style:\n" + mode_hint)
    parts.append("User message:\n" + (user_text or "").strip())
    return "\n\n".join(parts).strip()


async def _bot_api_call(bot: Bot, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = _get_bot_token(bot)
    url = f"https://api.telegram.org/bot{token}/{method}"

    session = _get_aiohttp_session(bot)
    if session is None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as tmp:
            async with tmp.post(url, json=payload) as resp:
                data = await resp.json(content_type=None)
    else:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json(content_type=None)

    if not isinstance(data, dict):
        raise RuntimeError(f"{method} failed: {data}")
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data}")
    return data


async def _delete_message_api(bot: Bot, *, chat_id: int, message_id: int) -> None:
    try:
        await _bot_api_call(bot, "deleteMessage", {"chat_id": int(chat_id), "message_id": int(message_id)})
    except Exception:
        return


async def _delete_messages_best_effort(bot: Bot, *, chat_id: int, message_ids: List[int]) -> None:
    ids = [int(x) for x in message_ids if x]
    if not ids:
        return
    sem = asyncio.Semaphore(8)

    async def _one(mid: int) -> None:
        async with sem:
            await _delete_message_api(bot, chat_id=chat_id, message_id=mid)

    await asyncio.gather(*(_one(mid) for mid in ids), return_exceptions=True)


async def _send_message_api(
    bot: Bot,
    *,
    chat_id: int,
    message_thread_id: Optional[int] = None,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _bot_api_call(bot, "sendMessage", payload)


async def _edit_message_text_api(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _bot_api_call(bot, "editMessageText", payload)

async def _edit_markdown_v2_message_api(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        await _edit_message_text_api(
            bot,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        return
    except Exception:
        pass
    try:
        await _edit_message_text_api(
            bot,
            chat_id=chat_id,
            message_id=message_id,
            text=_sanitize_markdown_v2(text),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        return
    except Exception:
        pass
    await _edit_message_text_api(
        bot,
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=reply_markup,
    )


async def _send_message_draft(
    bot: Bot,
    *,
    chat_id: int,
    message_thread_id: Optional[int],
    draft_id: int,
    text: str,
    parse_mode: Optional[str] = None,
) -> None:
    token = _get_bot_token(bot)
    url = f"https://api.telegram.org/bot{token}/sendMessageDraft"
    payload = {"chat_id": chat_id, "draft_id": draft_id, "text": text}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    if parse_mode:
        payload["parse_mode"] = parse_mode

    session = _get_aiohttp_session(bot)
    if session is None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as tmp:
            async with tmp.post(url, json=payload) as resp:
                data = await resp.json(content_type=None)
    else:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json(content_type=None)

    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"sendMessageDraft failed: {data}")


async def _answer_markdown_v2(message: Message, text: str, *, message_thread_id: Optional[int]) -> Optional[int]:
    try:
        sent = await message.answer(text, parse_mode="MarkdownV2", message_thread_id=message_thread_id)
        return int(sent.message_id) if getattr(sent, "message_id", None) else None
    except Exception:
        try:
            sent = await message.answer(_sanitize_markdown_v2(text), parse_mode="MarkdownV2", message_thread_id=message_thread_id)
            return int(sent.message_id) if getattr(sent, "message_id", None) else None
        except Exception:
            try:
                sent = await message.answer(text, message_thread_id=message_thread_id)
                return int(sent.message_id) if getattr(sent, "message_id", None) else None
            except Exception:
                return None


async def _edit_markdown_v2(message: Message, text: str) -> None:
    try:
        await message.edit_text(text, parse_mode="MarkdownV2")
    except Exception:
        try:
            await message.edit_text(_sanitize_markdown_v2(text), parse_mode="MarkdownV2")
        except Exception:
            try:
                await message.edit_text(text)
            except Exception:
                return


async def _is_channel_member(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    status = str(getattr(member, "status", ""))
    if status in {"member", "administrator", "creator"}:
        return True
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return False


def _with_duration(text: str, duration_ms: int, *, show_duration: bool) -> str:
    base = (text or " ").rstrip() or " "
    if not show_duration:
        return base
    seconds = max(0.0, duration_ms / 1000.0)
    return f"{base}\n\n⏱ {seconds:.1f}s"


def _kb_actions(lang: str, assistant_message_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": t(lang, "btn_summarize"), "callback_data": f"sum:{assistant_message_id}", "style": "success"},
                {"text": t(lang, "btn_explain"), "callback_data": f"exp:{assistant_message_id}", "style": "primary"},
            ],
        ]
    }


async def _send_markdown_v2_message_api(
    bot: Bot,
    *,
    chat_id: int,
    message_thread_id: Optional[int] = None,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    try:
        data = await _send_message_api(
            bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            text=text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        return int(((data.get("result") or {}).get("message_id")) or 0) or None
    except Exception:
        try:
            data = await _send_message_api(
                bot,
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                text=_sanitize_markdown_v2(text),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
            return int(((data.get("result") or {}).get("message_id")) or 0) or None
        except Exception:
            data = await _send_message_api(bot, chat_id=chat_id, message_thread_id=message_thread_id, text=text, reply_markup=reply_markup)
            return int(((data.get("result") or {}).get("message_id")) or 0) or None


async def _stream_to_chat(
    message: Message,
    copilot: CopilotClient,
    prompt: str,
    lang: str,
    *,
    user_id: int,
    storage: Storage,
    assistant_message_id: int,
    show_duration: bool,
    store_enabled: bool,
    enable_actions: bool,
) -> Tuple[str, int]:
    started_at = time.monotonic()
    chat_id = message.chat.id
    thread_id = _get_thread_id(message)
    draft_id = _new_draft_id()
    draft_markdown_enabled = True
    full_text = ""
    try:
        await _send_message_draft(message.bot, chat_id=chat_id, message_thread_id=thread_id, draft_id=draft_id, text=t(lang, "thinking"))
    except Exception:
        placeholder = await message.answer(t(lang, "thinking"), message_thread_id=thread_id)
        if store_enabled:
            try:
                await storage.add_topic_message_id(
                    user_id=user_id,
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    telegram_message_id=int(placeholder.message_id),
                    owner="bot",
                )
            except Exception:
                pass
        buffer = ""
        last_update_at = 0.0
        last_sent_len = 0
        min_interval_s = 0.25
        min_chars_delta = 24

        async def update_placeholder(force: bool = False) -> None:
            nonlocal last_update_at, last_sent_len
            now = time.monotonic()
            if not force:
                if (now - last_update_at) < min_interval_s and (len(buffer) - last_sent_len) < min_chars_delta:
                    return
            text = (buffer.strip() or t(lang, "thinking"))[:4096]
            await _edit_markdown_v2(placeholder, text)
            last_update_at = now
            last_sent_len = len(buffer)

        try:
            async for delta in copilot.ask_stream(prompt, language=lang):
                if delta:
                    buffer += delta
                    full_text += delta
                    try:
                        await update_placeholder()
                    except Exception:
                        pass
        except Exception:
            await _edit_markdown_v2(placeholder, t(lang, "error_ai"))
            return "", int((time.monotonic() - started_at) * 1000)

        final_text = buffer.strip() or t(lang, "thinking")
        duration_ms = int((time.monotonic() - started_at) * 1000)
        if store_enabled and assistant_message_id:
            await storage.update_message(assistant_message_id, text=final_text, duration_ms=duration_ms, telegram_message_id=placeholder.message_id)
        actions = _kb_actions(lang, assistant_message_id) if enable_actions and assistant_message_id else None
        parts = _split_telegram_text(_with_duration(final_text, duration_ms, show_duration=show_duration))
        try:
            await _edit_message_text_api(
                message.bot,
                chat_id=chat_id,
                message_id=placeholder.message_id,
                text=parts[0],
                parse_mode="MarkdownV2",
                reply_markup=actions,
            )
        except Exception:
            try:
                await _edit_message_text_api(
                    message.bot,
                    chat_id=chat_id,
                    message_id=placeholder.message_id,
                    text=parts[0],
                    reply_markup=actions,
                )
            except Exception:
                await _edit_markdown_v2(placeholder, parts[0])
        for part in parts[1:]:
            mid = await _answer_markdown_v2(message, part, message_thread_id=thread_id)
            if store_enabled and mid:
                try:
                    await storage.add_topic_message_id(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        telegram_message_id=int(mid),
                        owner="bot",
                    )
                except Exception:
                    pass
        return final_text, duration_ms

    draft_enabled = True
    chunk_limit = 3900
    min_interval_s = 0.25
    min_chars_delta = 24
    last_update_at = 0.0
    last_sent_len = 0
    buffer = ""

    async def update_draft(force: bool = False) -> None:
        nonlocal last_update_at, last_sent_len, draft_id, draft_enabled, draft_markdown_enabled
        if not draft_enabled:
            return
        now = time.monotonic()
        if not force:
            if (now - last_update_at) < min_interval_s and (len(buffer) - last_sent_len) < min_chars_delta:
                return
        text = (buffer.strip() or t(lang, "thinking"))[:4096]
        try:
            if draft_markdown_enabled:
                await _send_message_draft(
                    message.bot,
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    draft_id=draft_id,
                    text=text,
                    parse_mode="MarkdownV2",
                )
            else:
                await _send_message_draft(message.bot, chat_id=chat_id, message_thread_id=thread_id, draft_id=draft_id, text=text)
        except Exception:
            if draft_markdown_enabled:
                draft_markdown_enabled = False
                try:
                    await _send_message_draft(message.bot, chat_id=chat_id, message_thread_id=thread_id, draft_id=draft_id, text=text)
                except Exception:
                    draft_enabled = False
                    return
            else:
                draft_enabled = False
                return
        last_update_at = now
        last_sent_len = len(buffer)

    async def finalize_chunk(prepare_next_draft: bool) -> None:
        nonlocal buffer, draft_id, last_update_at, last_sent_len, draft_enabled
        text = buffer.strip() or " "
        await update_draft(force=True)
        if not prepare_next_draft:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            final_text = full_text.strip() or text
            actions = _kb_actions(lang, assistant_message_id) if enable_actions and assistant_message_id else None
            sent_id = await _send_markdown_v2_message_api(
                message.bot,
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=_with_duration(final_text, duration_ms, show_duration=show_duration),
                reply_markup=actions,
            )
            if store_enabled and sent_id:
                try:
                    await storage.add_topic_message_id(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        telegram_message_id=int(sent_id),
                        owner="bot",
                    )
                except Exception:
                    pass
            if store_enabled and assistant_message_id:
                await storage.update_message(assistant_message_id, text=final_text, duration_ms=duration_ms, telegram_message_id=sent_id)
        else:
            mid = await _answer_markdown_v2(message, text, message_thread_id=thread_id)
            if store_enabled and mid:
                try:
                    await storage.add_topic_message_id(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        telegram_message_id=int(mid),
                        owner="bot",
                    )
                except Exception:
                    pass
        buffer = ""
        last_update_at = 0.0
        last_sent_len = 0
        if not draft_enabled:
            return
        if prepare_next_draft:
            draft_id = _new_draft_id()
            try:
                await _send_message_draft(message.bot, chat_id=chat_id, message_thread_id=thread_id, draft_id=draft_id, text=t(lang, "thinking"))
            except Exception:
                draft_enabled = False

    try:
        async for delta in copilot.ask_stream(prompt, language=lang):
            if not delta:
                continue
            buffer += delta
            full_text += delta

            while len(buffer) > chunk_limit:
                part = buffer[:chunk_limit]
                rest = buffer[chunk_limit:]
                buffer = part
                await finalize_chunk(prepare_next_draft=True)
                buffer = rest

            await update_draft()

        if buffer:
            await finalize_chunk(prepare_next_draft=False)
        else:
            buffer = " "
            await finalize_chunk(prepare_next_draft=False)
    except Exception:
        await message.answer(t(lang, "error_ai"), message_thread_id=thread_id)
        return "", int((time.monotonic() - started_at) * 1000)

    return full_text.strip() or " ", int((time.monotonic() - started_at) * 1000)


def build_dispatcher(copilot: CopilotClient, storage: Storage) -> Dispatcher:
    router = Router()
    user_lang: Dict[int, str] = {}
    verified_users: Dict[int, bool] = {}

    def _lang_for(user_id: int) -> str:
        return user_lang.get(user_id, "en")

    def _ik_btn(text: str, *, callback_data: Optional[str] = None, url: Optional[str] = None, style: Optional[str] = None) -> Dict[str, Any]:
        data: Dict[str, Any] = {"text": text}
        if callback_data is not None:
            data["callback_data"] = callback_data
        if url is not None:
            data["url"] = url
        if style is not None:
            data["style"] = style
        return data

    async def _edit_or_send(
        *,
        callback: CallbackQuery,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = callback.message
        thread_id = getattr(msg, "message_thread_id", None) if msg else None
        if msg is not None:
            try:
                await _edit_markdown_v2_message_api(
                    callback.bot,
                    chat_id=msg.chat.id,
                    message_id=msg.message_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                return
            except Exception:
                pass
        chat_id = msg.chat.id if msg is not None else callback.from_user.id
        await _send_markdown_v2_message_api(callback.bot, chat_id=chat_id, message_thread_id=thread_id, text=text, reply_markup=reply_markup)

    def _kb_help(lang: str) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    _ik_btn(t(lang, "menu_settings"), callback_data="cmd:settings", style="primary"),
                    _ik_btn(t(lang, "menu_lang"), callback_data="cmd:lang", style="primary"),
                ],
                [
                    _ik_btn(t(lang, "menu_history"), callback_data="cmd:history", style="primary"),
                    _ik_btn(t(lang, "menu_stats"), callback_data="cmd:stats", style="primary"),
                ],
                [
                    _ik_btn(t(lang, "menu_profile"), callback_data="cmd:profile", style="primary"),
                    _ik_btn(t(lang, "menu_about"), callback_data="cmd:about", style="primary"),
                ],
            ]
        }

    def _kb_settings(lang: str, *, show_duration: bool, response_mode: str, private_mode: bool) -> Dict[str, Any]:
        dur_label = t(lang, "dur_on") if show_duration else t(lang, "dur_off")
        dur_style = "success" if show_duration else "danger"
        mode = (response_mode or "normal").strip().lower()
        mode_label = {
            "short": t(lang, "mode_label_short"),
            "normal": t(lang, "mode_label_normal"),
            "detailed": t(lang, "mode_label_detailed"),
            "code": t(lang, "mode_label_code"),
        }.get(mode, t(lang, "mode_label_normal"))
        priv_label = t(lang, "private_on") if private_mode else t(lang, "private_off")
        priv_style = "success" if private_mode else "danger"

        def st(selected: bool) -> str:
            return "success" if selected else "danger"

        return {
            "inline_keyboard": [
                [
                    _ik_btn(dur_label, callback_data="set:dur", style=dur_style),
                    _ik_btn(mode_label, callback_data="noop:mode"),
                ],
                [
                    _ik_btn(priv_label, callback_data="set:priv", style=priv_style),
                    _ik_btn(" ", callback_data="noop:priv"),
                ],
                [
                    _ik_btn(t(lang, "mode_short"), callback_data="set:mode:short", style=st(mode == "short")),
                    _ik_btn(t(lang, "mode_normal"), callback_data="set:mode:normal", style=st(mode == "normal")),
                ],
                [
                    _ik_btn(t(lang, "mode_detailed"), callback_data="set:mode:detailed", style=st(mode == "detailed")),
                    _ik_btn(t(lang, "mode_code"), callback_data="set:mode:code", style=st(mode == "code")),
                ],
                [
                    _ik_btn(t(lang, "btn_reset_thread"), callback_data="confirm:reset_thread", style="danger"),
                    _ik_btn(t(lang, "btn_reset_all"), callback_data="confirm:reset_all", style="danger"),
                ],
                [
                    _ik_btn(t(lang, "menu_help"), callback_data="cmd:help", style="primary"),
                ],
            ]
        }

    def _kb_confirm(lang: str, action: str) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    _ik_btn(t(lang, "btn_confirm"), callback_data=f"do:{action}", style="success"),
                    _ik_btn(t(lang, "btn_cancel"), callback_data="do:cancel", style="primary"),
                ]
            ]
        }

    async def _send_help(chat_id: int, *, bot: Bot, thread_id: Optional[int], lang: str) -> None:
        text = t(lang, "help_text")
        await _send_markdown_v2_message_api(bot, chat_id=chat_id, message_thread_id=thread_id, text=text, reply_markup=_kb_help(lang))

    async def _send_about(chat_id: int, *, bot: Bot, thread_id: Optional[int], lang: str) -> None:
        text = t(lang, "about_text")
        kb = {"inline_keyboard": [[_ik_btn(t(lang, "menu_channel"), url=CHANNEL_URL, style="primary")]]}
        await _send_markdown_v2_message_api(bot, chat_id=chat_id, message_thread_id=thread_id, text=text, reply_markup=kb)

    async def _require_verified_message(message: Message, *, lang: str) -> bool:
        if not message.from_user:
            return False
        if verified_users.get(message.from_user.id, False):
            return True
        await _send_message_api(message.bot, chat_id=message.chat.id, message_thread_id=_get_thread_id(message), text=t(lang, "join_required"), reply_markup=kb_join(lang))
        return False

    @router.message(CommandStart())
    async def start_handler(message: Message) -> None:
        if not message.from_user:
            return
        lc = (getattr(message.from_user, "language_code", None) or "").split("-", 1)[0].strip().lower()
        lang_guess = lc if lc in SUPPORTED_LANGS else "en"
        thread_id = _get_thread_id(message)
        await storage.track_chat(message.chat.id)
        first_time = not await storage.user_exists(message.from_user.id)
        await storage.upsert_user(
            message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name or "",
            language=lang_guess,
            verified=False,
        )
        verified_users[message.from_user.id] = False
        await _set_commands_for_user(message.bot, chat_id=message.chat.id, user_id=message.from_user.id, lang=lang_guess)
        if first_time:
            users = await storage.count_users()
            chats = await storage.count_chats()
            await _send_message_api(
                message.bot,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                text=t(lang_guess, "start_welcome").format(users=users, chats=chats),
            )
        await _send_message_api(message.bot, chat_id=message.chat.id, message_thread_id=thread_id, text=t(lang_guess, "choose_language"), reply_markup=kb_language(lang_guess))

    @router.message(Command("help"))
    async def help_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        await _send_help(message.chat.id, bot=message.bot, thread_id=_get_thread_id(message), lang=lang)

    @router.message(Command("about"))
    async def about_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        await _send_about(message.chat.id, bot=message.bot, thread_id=_get_thread_id(message), lang=lang)

    @router.message(Command("lang"))
    async def lang_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        await _send_message_api(message.bot, chat_id=message.chat.id, message_thread_id=_get_thread_id(message), text=t(lang, "choose_language"), reply_markup=kb_language(lang))

    @router.message(Command("settings"))
    async def settings_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        defaults = await storage.get_user_settings(message.from_user.id)
        await storage.ensure_thread_settings(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_thread_id=_get_thread_id(message),
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        settings = await storage.get_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=_get_thread_id(message))
        show_duration = bool(settings.get("show_duration", True))
        response_mode = str(settings.get("response_mode", "normal"))
        private_mode = bool(settings.get("private_mode", False))
        text = t(lang, "settings_text")
        await _send_markdown_v2_message_api(
            message.bot,
            chat_id=message.chat.id,
            message_thread_id=_get_thread_id(message),
            text=text,
            reply_markup=_kb_settings(lang, show_duration=show_duration, response_mode=response_mode, private_mode=private_mode),
        )

    async def _render_profile(*, user_id: int, lang: str, cleared: bool = False) -> Tuple[str, Dict[str, Any]]:
        facts = await storage.list_profile_facts(user_id=user_id, limit=24)
        divider = "━━━━━━━━━━━━"
        count_label = f"تعداد فکت\u200cها: {len(facts)}" if lang == "fa" else f"Facts: {len(facts)}"
        lines: List[str] = [t(lang, "profile_title"), divider]
        if cleared:
            lines.append(t(lang, "profile_cleared"))
        if not facts:
            lines.extend(["", t(lang, "profile_empty")])
        else:
            lines.extend([count_label, ""])
            for fct in facts[:24]:
                s = (fct or "").strip()
                if not s:
                    continue
                lines.append(f"• {s}")
        kb = {
            "inline_keyboard": [
                [
                    _ik_btn(t(lang, "btn_refresh"), callback_data="profile:refresh", style="primary"),
                    _ik_btn(t(lang, "btn_profile_clear"), callback_data="profile:clear", style="danger"),
                ]
            ]
        }
        return "\n".join(lines).strip(), kb

    async def _send_profile(chat_id: int, *, bot: Bot, thread_id: Optional[int], lang: str, user_id: int) -> None:
        text, kb = await _render_profile(user_id=user_id, lang=lang)
        await _send_markdown_v2_message_api(bot, chat_id=chat_id, message_thread_id=thread_id, text=text, reply_markup=kb)

    async def _render_history(
        *,
        user_id: int,
        chat_id: int,
        thread_id: Optional[int],
        lang: str,
        page: int = 0,
    ) -> Tuple[str, Dict[str, Any]]:
        page_size = 10
        page = max(0, int(page))
        total = await storage.count_visible_messages_in_thread(user_id=user_id, chat_id=chat_id, message_thread_id=thread_id)
        pages = max(1, (total + page_size - 1) // page_size)
        if page >= pages:
            page = max(0, pages - 1)
        offset = page * page_size
        msgs = await storage.get_visible_messages_page_in_thread(
            user_id=user_id,
            chat_id=chat_id,
            message_thread_id=thread_id,
            limit=page_size,
            offset=offset,
        )
        divider = "━━━━━━━━━━━━"
        title = t(lang, "history_title")
        topic_name = _topic_name(thread_id)
        topic_label = f"تاپیک: {topic_name}" if lang == "fa" else f"Topic: {topic_name}"
        prev_cb = f"history:page:{page - 1}" if page > 0 else "noop:hist_prev"
        next_cb = f"history:page:{page + 1}" if page + 1 < pages else "noop:hist_next"
        refresh_cb = f"history:page:{page}"
        kb = {
            "inline_keyboard": [
                [
                    _ik_btn(t(lang, "btn_prev"), callback_data=prev_cb, style="primary"),
                    _ik_btn(t(lang, "btn_refresh"), callback_data=refresh_cb, style="primary"),
                    _ik_btn(t(lang, "btn_next"), callback_data=next_cb, style="primary"),
                ],
                [
                    _ik_btn(t(lang, "btn_reset_thread"), callback_data="confirm:reset_thread", style="danger"),
                ],
            ]
        }
        if not msgs:
            return f"{title}\n{divider}\n\n{t(lang, 'history_empty')}", kb

        lines: List[str] = [title, divider, topic_label]
        if lang == "fa":
            lines.append(f"صفحه: {page + 1} / {pages}")
        else:
            lines.append(f"Page: {page + 1} / {pages}")
        topic_summary = await storage.get_topic_summary(user_id=user_id, chat_id=chat_id, message_thread_id=thread_id)
        if topic_summary:
            summary_title = "خلاصه تاپیک:" if lang == "fa" else "Topic summary:"
            lines.extend(["", summary_title, _shorten(topic_summary, 700)])
        lines.extend(["", t(lang, "history_subtitle"), ""])
        for m in msgs:
            txt = (m.text or "").strip()
            if not txt:
                continue
            prefix = "U" if m.role == "user" else "A"
            lines.append(f"• {prefix}: {_shorten(txt, 220)}")
        return "\n".join(lines).strip(), kb

    async def _send_history(target_chat_id: int, *, bot: Bot, thread_id: Optional[int], lang: str, user_id: int) -> None:
        tset = await storage.get_thread_settings(user_id=user_id, chat_id=target_chat_id, message_thread_id=thread_id)
        if bool(tset.get("private_mode", False)):
            await _send_markdown_v2_message_api(bot, chat_id=target_chat_id, message_thread_id=thread_id, text=t(lang, "history_empty"))
            return
        text, kb = await _render_history(user_id=user_id, chat_id=target_chat_id, thread_id=thread_id, lang=lang)
        await _send_markdown_v2_message_api(bot, chat_id=target_chat_id, message_thread_id=thread_id, text=text, reply_markup=kb)

    @router.message(Command("profile"))
    async def profile_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        await _send_profile(message.chat.id, bot=message.bot, thread_id=_get_thread_id(message), lang=lang, user_id=message.from_user.id)

    @router.message(Command("mode"))
    async def mode_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        defaults = await storage.get_user_settings(message.from_user.id)
        await storage.ensure_thread_settings(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_thread_id=_get_thread_id(message),
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 2:
            mode = parts[1].strip().lower()
            if mode in {"short", "normal", "detailed", "code"}:
                await storage.update_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=_get_thread_id(message), response_mode=mode, asked_private_mode=True)
                settings = await storage.get_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=_get_thread_id(message))
                mode_view = {
                    "short": t(lang, "mode_short"),
                    "normal": t(lang, "mode_normal"),
                    "detailed": t(lang, "mode_detailed"),
                    "code": t(lang, "mode_code"),
                }.get(mode, t(lang, "mode_normal"))
                await _send_markdown_v2_message_api(
                    message.bot,
                    chat_id=message.chat.id,
                    message_thread_id=_get_thread_id(message),
                    text=t(lang, "mode_set").format(mode=mode_view),
                    reply_markup=_kb_settings(
                        lang,
                        show_duration=bool(settings.get("show_duration", True)),
                        response_mode=str(settings.get("response_mode", "normal")),
                        private_mode=bool(settings.get("private_mode", False)),
                    ),
                )
                return
        await settings_cmd(message)

    @router.message(Command("history"))
    async def history_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        thread_id = _get_thread_id(message)
        await _send_history(message.chat.id, bot=message.bot, thread_id=thread_id, lang=lang, user_id=message.from_user.id)

    @router.message(Command("reset"))
    async def reset_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        thread_id = _get_thread_id(message)
        try:
            await storage.add_topic_message_id(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                telegram_message_id=int(message.message_id),
                owner="user",
            )
        except Exception:
            pass
        sent_id = await _send_markdown_v2_message_api(
            message.bot,
            chat_id=message.chat.id,
            message_thread_id=thread_id,
            text=t(lang, "reset_thread_prompt"),
            reply_markup=_kb_confirm(lang, "reset_thread"),
        )
        if sent_id:
            try:
                await storage.add_topic_message_id(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    message_thread_id=thread_id,
                    telegram_message_id=int(sent_id),
                    owner="bot",
                )
            except Exception:
                pass

    @router.message(Command("reset_all"))
    async def reset_all_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        thread_id = _get_thread_id(message)
        try:
            await storage.add_topic_message_id(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                telegram_message_id=int(message.message_id),
                owner="user",
            )
        except Exception:
            pass
        sent_id = await _send_markdown_v2_message_api(
            message.bot,
            chat_id=message.chat.id,
            message_thread_id=thread_id,
            text=t(lang, "reset_all_prompt"),
            reply_markup=_kb_confirm(lang, "reset_all"),
        )
        if sent_id:
            try:
                await storage.add_topic_message_id(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    message_thread_id=thread_id,
                    telegram_message_id=int(sent_id),
                    owner="bot",
                )
            except Exception:
                pass

    @router.message(Command("clear"))
    async def clear_cmd(message: Message) -> None:
        await reset_cmd(message)

    @router.message(Command("stats"))
    async def stats_cmd(message: Message) -> None:
        if not message.from_user:
            return
        lang = _lang_for(message.from_user.id)
        if not await _require_verified_message(message, lang=lang):
            return
        total, first_ts = await storage.get_user_message_stats(user_id=message.from_user.id, chat_id=message.chat.id)
        tset = await storage.get_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=_get_thread_id(message))
        show_duration = t(lang, "on") if bool(tset.get("show_duration", True)) else t(lang, "off")
        response_mode = str(tset.get("response_mode", "normal"))
        mode_view = {
            "short": t(lang, "mode_short"),
            "normal": t(lang, "mode_normal"),
            "detailed": t(lang, "mode_detailed"),
            "code": t(lang, "mode_code"),
        }.get(response_mode.strip().lower(), t(lang, "mode_normal"))
        text = (
            f"{t(lang, 'stats_title')}\n\n"
            f"{t(lang, 'stats_messages').format(count=total)}\n"
            f"{t(lang, 'stats_duration').format(value=show_duration)}\n"
            f"{t(lang, 'stats_mode').format(value=mode_view)}\n"
            f"{t(lang, 'private_on' if bool(tset.get('private_mode', False)) else 'private_off')}"
        )
        await _send_markdown_v2_message_api(message.bot, chat_id=message.chat.id, message_thread_id=_get_thread_id(message), text=text)

    @router.callback_query(F.data.startswith("cmd:"))
    async def cmd_menu_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        await storage.track_chat(callback.message.chat.id)
        lang = _lang_for(callback.from_user.id)
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        if callback.data == "cmd:help":
            await _edit_or_send(callback=callback, text=t(lang, "help_text"), reply_markup=_kb_help(lang))
        elif callback.data == "cmd:about":
            kb = {"inline_keyboard": [[_ik_btn(t(lang, "menu_channel"), url=CHANNEL_URL, style="primary")]]}
            await _edit_or_send(callback=callback, text=t(lang, "about_text"), reply_markup=kb)
        elif callback.data == "cmd:profile":
            text, kb = await _render_profile(user_id=callback.from_user.id, lang=lang)
            await _edit_or_send(callback=callback, text=text, reply_markup=kb)
        elif callback.data == "cmd:lang":
            await _edit_or_send(callback=callback, text=t(lang, "choose_language"), reply_markup=kb_language(lang))
        elif callback.data == "cmd:settings":
            if not verified_users.get(callback.from_user.id, False):
                await _edit_or_send(callback=callback, text=t(lang, "join_required"), reply_markup=kb_join(lang))
                return
            defaults = await storage.get_user_settings(callback.from_user.id)
            await storage.ensure_thread_settings(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                default_show_duration=bool(defaults.get("show_duration", True)),
                default_response_mode=str(defaults.get("response_mode", "normal")),
            )
            settings = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            await _edit_or_send(
                callback=callback,
                text=t(lang, "settings_text"),
                reply_markup=_kb_settings(
                    lang,
                    show_duration=bool(settings.get("show_duration", True)),
                    response_mode=str(settings.get("response_mode", "normal")),
                    private_mode=bool(settings.get("private_mode", False)),
                ),
            )
        elif callback.data == "cmd:history":
            if not verified_users.get(callback.from_user.id, False):
                await _edit_or_send(callback=callback, text=t(lang, "join_required"), reply_markup=kb_join(lang))
                return
            tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            if bool(tset.get("private_mode", False)):
                await _edit_or_send(callback=callback, text=t(lang, "history_empty"), reply_markup=_kb_help(lang))
                return
            text, kb = await _render_history(user_id=callback.from_user.id, chat_id=callback.message.chat.id, thread_id=thread_id, lang=lang)
            await _edit_or_send(callback=callback, text=text, reply_markup=kb)
        elif callback.data == "cmd:stats":
            if not verified_users.get(callback.from_user.id, False):
                await _edit_or_send(callback=callback, text=t(lang, "join_required"), reply_markup=kb_join(lang))
                return
            total, first_ts = await storage.get_user_message_stats(user_id=callback.from_user.id, chat_id=callback.message.chat.id)
            tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            show_duration = t(lang, "on") if bool(tset.get("show_duration", True)) else t(lang, "off")
            response_mode = str(tset.get("response_mode", "normal"))
            mode_view = {
                "short": t(lang, "mode_short"),
                "normal": t(lang, "mode_normal"),
                "detailed": t(lang, "mode_detailed"),
                "code": t(lang, "mode_code"),
            }.get(response_mode.strip().lower(), t(lang, "mode_normal"))
            text = (
                f"{t(lang, 'stats_title')}\n\n"
                f"{t(lang, 'stats_messages').format(count=total)}\n"
                f"{t(lang, 'stats_duration').format(value=show_duration)}\n"
                f"{t(lang, 'stats_mode').format(value=mode_view)}\n"
                f"{t(lang, 'private_on' if bool(tset.get('private_mode', False)) else 'private_off')}"
            )
            await _edit_or_send(callback=callback, text=text, reply_markup=_kb_help(lang))
        elif callback.data == "cmd:mode":
            if not verified_users.get(callback.from_user.id, False):
                await _edit_or_send(callback=callback, text=t(lang, "join_required"), reply_markup=kb_join(lang))
                return
            defaults = await storage.get_user_settings(callback.from_user.id)
            await storage.ensure_thread_settings(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                default_show_duration=bool(defaults.get("show_duration", True)),
                default_response_mode=str(defaults.get("response_mode", "normal")),
            )
            settings = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            await _edit_or_send(
                callback=callback,
                text=t(lang, "settings_text"),
                reply_markup=_kb_settings(
                    lang,
                    show_duration=bool(settings.get("show_duration", True)),
                    response_mode=str(settings.get("response_mode", "normal")),
                    private_mode=bool(settings.get("private_mode", False)),
                ),
            )

    @router.callback_query(F.data.startswith("set:"))
    async def settings_update_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        defaults = await storage.get_user_settings(callback.from_user.id)
        await storage.ensure_thread_settings(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        parts = (callback.data or "").split(":")
        if len(parts) >= 2 and parts[1] == "dur":
            cur = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            new_val = not bool(cur.get("show_duration", True))
            await storage.update_thread_settings(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                show_duration=new_val,
                asked_private_mode=True,
            )
        elif len(parts) >= 2 and parts[1] == "priv":
            cur = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            new_val = not bool(cur.get("private_mode", False))
            await storage.update_thread_settings(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                private_mode=new_val,
                asked_private_mode=True,
            )
        elif len(parts) == 3 and parts[1] == "mode":
            mode = parts[2].strip().lower()
            if mode in {"short", "normal", "detailed", "code"}:
                await storage.update_thread_settings(
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    message_thread_id=thread_id,
                    response_mode=mode,
                    asked_private_mode=True,
                )
        settings = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        await _edit_or_send(
            callback=callback,
            text=t(lang, "settings_text"),
            reply_markup=_kb_settings(
                lang,
                show_duration=bool(settings.get("show_duration", True)),
                response_mode=str(settings.get("response_mode", "normal")),
                private_mode=bool(settings.get("private_mode", False)),
            ),
        )

    @router.callback_query(F.data.startswith("confirm:"))
    async def confirm_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        action = (callback.data or "").split(":", 1)[-1]
        if action == "reset_thread":
            await _edit_or_send(callback=callback, text=t(lang, "confirm_final"), reply_markup=_kb_confirm(lang, "reset_thread"))
        elif action == "reset_all":
            await _edit_or_send(callback=callback, text=t(lang, "confirm_final"), reply_markup=_kb_confirm(lang, "reset_all"))

    @router.callback_query(F.data.startswith("do:"))
    async def do_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        lang = _lang_for(callback.from_user.id)
        action = (callback.data or "").split(":", 1)[-1]
        if action == "cancel":
            settings = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            await _edit_or_send(
                callback=callback,
                text=t(lang, "settings_text"),
                reply_markup=_kb_settings(
                    lang,
                    show_duration=bool(settings.get("show_duration", True)),
                    response_mode=str(settings.get("response_mode", "normal")),
                    private_mode=bool(settings.get("private_mode", False)),
                ),
            )
            return
        if action == "reset_thread":
            ids: List[int] = []
            try:
                ids.extend(await storage.list_topic_message_ids(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id))
            except Exception:
                pass
            try:
                ids.extend(await storage.list_telegram_message_ids_in_thread(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id))
            except Exception:
                pass
            ids = list({int(x) for x in ids if x})
            await _delete_messages_best_effort(callback.bot, chat_id=callback.message.chat.id, message_ids=ids)
            deleted = await storage.delete_topic_data(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
            await _edit_or_send(callback=callback, text=t(lang, "done_reset_thread").format(count=deleted), reply_markup=_kb_help(lang))

            async def _cleanup_confirm(mid: int) -> None:
                await asyncio.sleep(1.2)
                await _delete_message_api(callback.bot, chat_id=callback.message.chat.id, message_id=mid)

            asyncio.create_task(_cleanup_confirm(int(callback.message.message_id)))
        elif action == "reset_all":
            ids_all: List[int] = []
            try:
                ids_all.extend(await storage.list_topic_message_ids_in_chat(user_id=callback.from_user.id, chat_id=callback.message.chat.id))
            except Exception:
                pass
            try:
                ids_all.extend(await storage.list_telegram_message_ids_in_chat(user_id=callback.from_user.id, chat_id=callback.message.chat.id))
            except Exception:
                pass
            ids_all = list({int(x) for x in ids_all if x})
            await _delete_messages_best_effort(callback.bot, chat_id=callback.message.chat.id, message_ids=ids_all)
            deleted = await storage.delete_all_data_for_chat(user_id=callback.from_user.id, chat_id=callback.message.chat.id)
            await _edit_or_send(callback=callback, text=t(lang, "done_reset_all").format(count=deleted), reply_markup=_kb_help(lang))

            async def _cleanup_confirm_all(mid: int) -> None:
                await asyncio.sleep(1.2)
                await _delete_message_api(callback.bot, chat_id=callback.message.chat.id, message_id=mid)

            asyncio.create_task(_cleanup_confirm_all(int(callback.message.message_id)))

    @router.callback_query(F.data == "profile:clear")
    async def profile_clear_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        await storage.clear_profile_facts(user_id=callback.from_user.id)
        text, kb = await _render_profile(user_id=callback.from_user.id, lang=lang, cleared=True)
        await _edit_or_send(callback=callback, text=text, reply_markup=kb)

    @router.callback_query(F.data == "profile:refresh")
    async def profile_refresh_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        text, kb = await _render_profile(user_id=callback.from_user.id, lang=lang)
        await _edit_or_send(callback=callback, text=text, reply_markup=kb)

    @router.callback_query(F.data == "history:refresh")
    async def history_refresh_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        if bool(tset.get("private_mode", False)):
            await _edit_or_send(callback=callback, text=t(lang, "history_empty"), reply_markup=_kb_help(lang))
            return
        text, kb = await _render_history(user_id=callback.from_user.id, chat_id=callback.message.chat.id, thread_id=thread_id, lang=lang, page=0)
        await _edit_or_send(callback=callback, text=text, reply_markup=kb)

    @router.callback_query(F.data.startswith("history:page:"))
    async def history_page_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        if bool(tset.get("private_mode", False)):
            await _edit_or_send(callback=callback, text=t(lang, "history_empty"), reply_markup=_kb_help(lang))
            return
        raw = (callback.data or "").split(":", 2)[-1]
        try:
            page = int(raw)
        except Exception:
            page = 0
        text, kb = await _render_history(user_id=callback.from_user.id, chat_id=callback.message.chat.id, thread_id=thread_id, lang=lang, page=page)
        await _edit_or_send(callback=callback, text=text, reply_markup=kb)

    @router.callback_query(F.data == "lang_menu")
    async def lang_menu_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        await _edit_or_send(callback=callback, text=t(lang, "choose_language"), reply_markup=kb_language(lang))

    @router.callback_query(F.data.startswith("lang:"))
    async def lang_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        lang = (callback.data or "").split(":", 1)[-1].strip().lower()
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        user_lang[callback.from_user.id] = lang
        verified_users[callback.from_user.id] = False
        await storage.upsert_user(
            callback.from_user.id,
            username=callback.from_user.username or "",
            full_name=callback.from_user.full_name or "",
            language=lang,
            verified=False,
        )
        await _set_commands_for_user(callback.bot, chat_id=callback.message.chat.id, user_id=callback.from_user.id, lang=lang)
        markup = kb_join(lang)
        try:
            await _edit_message_text_api(
                callback.bot,
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=t(lang, "join_required"),
                reply_markup=markup,
            )
        except Exception:
            try:
                await _send_message_api(callback.bot, chat_id=callback.message.chat.id, message_thread_id=thread_id, text=t(lang, "join_required"), reply_markup=markup)
            except Exception:
                await _send_message_api(
                    callback.bot,
                    chat_id=callback.message.chat.id,
                    message_thread_id=thread_id,
                    text=t(lang, "join_required"),
                    reply_markup=_strip_style(markup) if _contains_style(markup) else markup,
                )

    @router.callback_query(F.data == "verify")
    async def verify_handler(callback: CallbackQuery) -> None:
        lang = user_lang.get(callback.from_user.id, "en")
        await callback.answer()
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        if callback.message is not None:
            await storage.track_chat(callback.message.chat.id)
        try:
            ok = await _is_channel_member(callback.bot, user_id=callback.from_user.id)
        except Exception:
            await callback.message.answer(t(lang, "error_membership"), message_thread_id=thread_id)
            return
        if not ok:
            await _send_message_api(callback.bot, chat_id=callback.message.chat.id, message_thread_id=thread_id, text=t(lang, "verify_failed"), reply_markup=kb_join(lang))
            return

        verified_users[callback.from_user.id] = True
        await storage.upsert_user(
            callback.from_user.id,
            username=callback.from_user.username or "",
            full_name=callback.from_user.full_name or "",
            language=lang,
            verified=True,
        )
        try:
            await _edit_message_text_api(
                callback.bot,
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=t(lang, "verified"),
            )
        except Exception:
            await _send_message_api(callback.bot, chat_id=callback.message.chat.id, message_thread_id=thread_id, text=t(lang, "verified"))

        full_name = (callback.from_user.full_name or "").strip()
        username = (callback.from_user.username or "").strip()
        username_text = f"@{username}" if username else "none"

        welcome_prompt = (
            "Create a short, friendly welcome message for a Telegram user.\n"
            f"Language: {lang}\n"
            "Write the welcome message in the given language.\n"
            f"Name: {full_name}\n"
            f"Username: {username_text}\n"
            "Reply with the welcome message only."
        )
        welcome_assistant_id = await storage.create_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            role="assistant",
            text="",
        )
        defaults = await storage.get_user_settings(callback.from_user.id)
        await storage.ensure_thread_settings(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        show_duration = bool(tset.get("show_duration", True))
        response_mode = str(tset.get("response_mode", "normal"))
        await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
        composed = await _compose_prompt(
            storage=storage,
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            current_thread_id=thread_id,
            response_mode=response_mode,
            private_mode=False,
            user_text=welcome_prompt,
            reply_to_telegram_message_id=None,
            reply_fallback_text="",
        )
        await _stream_to_chat(
            callback.message,
            copilot,
            composed,
            lang,
            user_id=callback.from_user.id,
            storage=storage,
            assistant_message_id=welcome_assistant_id,
            show_duration=show_duration,
            store_enabled=True,
            enable_actions=True,
        )
        await callback.message.answer(t(lang, "send_prompt"), message_thread_id=thread_id)

    @router.message(F.text)
    async def text_handler(message: Message) -> None:
        if not message.from_user:
            return
        thread_id = _get_thread_id(message)
        lang = user_lang.get(message.from_user.id)
        if not lang:
            await _send_message_api(message.bot, chat_id=message.chat.id, message_thread_id=thread_id, text=t("en", "choose_language"), reply_markup=kb_language("en"))
            return
        if not verified_users.get(message.from_user.id, False):
            await _send_message_api(message.bot, chat_id=message.chat.id, message_thread_id=thread_id, text=t(lang, "join_required"), reply_markup=kb_join(lang))
            return

        user_text = (message.text or "").strip()
        if not user_text:
            return
        if user_text.startswith("/"):
            return
        reply_to = getattr(message, "reply_to_message", None)
        reply_to_id = getattr(reply_to, "message_id", None) if reply_to else None
        reply_fallback_text = ((getattr(reply_to, "text", None) or getattr(reply_to, "caption", None)) if reply_to else "") or ""

        await storage.track_chat(message.chat.id)
        await storage.upsert_user(
            message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name or "",
            language=lang,
            verified=True,
        )

        def _kb_private_prompt(cur_lang: str) -> Dict[str, Any]:
            return {
                "inline_keyboard": [
                    [
                        _ik_btn(t(cur_lang, "btn_private_on"), callback_data="topic_priv:on", style="success"),
                        _ik_btn(t(cur_lang, "btn_private_off"), callback_data="topic_priv:off", style="danger"),
                    ]
                ]
            }

        def _parse_nlp_lines(raw: str, *, limit: int) -> List[str]:
            seen: Dict[str, bool] = {}
            out: List[str] = []
            for line in (raw or "").splitlines():
                s = line.strip()
                if not s:
                    continue
                if s[:1] in {"-", "•", "*"}:
                    s = s[1:].strip()
                if len(s) >= 2 and s[0].isdigit() and s[1] in {".", ")"}:
                    s = s[2:].strip()
                s = " ".join(s.split())
                if not s or len(s) > 140:
                    continue
                key = s.casefold()
                if key in seen:
                    continue
                seen[key] = True
                out.append(s)
                if len(out) >= int(limit):
                    break
            return out

        async def _run_profile_facts_nlp(*, user_id: int, chat_id: int, lang_code: str) -> None:
            msgs = await storage.get_recent_texts_by_role(user_id=user_id, chat_id=chat_id, role="user", limit=10)
            body = "\n".join(f"- {m.strip()}" for m in msgs if (m or "").strip())
            if not body.strip():
                return
            prompt = (
                f"Language: {lang_code}\n"
                "Extract up to 8 stable profile facts about the user from the messages.\n"
                "Only include useful, long-term facts (name, location, preferences, background).\n"
                "Do not include sensitive data.\n"
                "Return one fact per line, no numbering, no extra text.\n\n"
                "Messages:\n"
                f"{body}"
            )
            raw = await copilot.ask(prompt, language=lang_code, priority=10)
            facts = _parse_nlp_lines(raw, limit=8)
            for fct in facts:
                await storage.add_profile_fact(user_id=user_id, fact=fct)

        async def _run_topic_summary_nlp(*, user_id: int, chat_id: int, message_thread_id: Optional[int], lang_code: str) -> None:
            msgs = await storage.get_recent_texts_by_role(
                user_id=user_id,
                chat_id=chat_id,
                role="user",
                limit=20,
                message_thread_id=message_thread_id,
                any_thread=False,
            )
            body = "\n".join(f"- {m.strip()}" for m in msgs if (m or "").strip())
            if not body.strip():
                return
            prompt = (
                f"Language: {lang_code}\n"
                "Summarize the current topic for future context.\n"
                "Keep it concise (1-3 sentences).\n"
                "Return the summary only.\n\n"
                "User messages:\n"
                f"{body}"
            )
            summary = (await copilot.ask(prompt, language=lang_code, priority=10)).strip()
            if len(summary) > 900:
                summary = summary[:900].rstrip() + "…"
            await storage.upsert_topic_summary(user_id=user_id, chat_id=chat_id, message_thread_id=message_thread_id, summary=summary)

        async def _maybe_enqueue_nlp(*, user_id: int, chat_id: int, message_thread_id: Optional[int], lang_code: str) -> None:
            try:
                total_user = await storage.count_messages_by_role(user_id=user_id, chat_id=chat_id, role="user")
                if total_user > 0 and total_user % 10 == 0:
                    await _run_profile_facts_nlp(user_id=user_id, chat_id=chat_id, lang_code=lang_code)
                topic_user = await storage.count_messages_by_role(
                    user_id=user_id,
                    chat_id=chat_id,
                    role="user",
                    message_thread_id=message_thread_id,
                    any_thread=False,
                )
                if topic_user > 0 and topic_user % 10 == 0:
                    await _run_topic_summary_nlp(user_id=user_id, chat_id=chat_id, message_thread_id=message_thread_id, lang_code=lang_code)
            except Exception:
                return

        async def _process_prompt(
            *,
            ctx_message: Message,
            telegram_message_id: Optional[int],
            prompt_text: str,
            reply_to_message_id: Optional[int],
            reply_fallback: str,
        ) -> None:
            defaults = await storage.get_user_settings(message.from_user.id)
            await storage.ensure_thread_settings(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                default_show_duration=bool(defaults.get("show_duration", True)),
                default_response_mode=str(defaults.get("response_mode", "normal")),
            )
            tset = await storage.get_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=thread_id)
            show_duration = bool(tset.get("show_duration", True))
            response_mode = str(tset.get("response_mode", "normal"))
            private_mode = bool(tset.get("private_mode", False))
            store_enabled = not private_mode

            composed = await _compose_prompt(
                storage=storage,
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                current_thread_id=thread_id,
                response_mode=response_mode,
                private_mode=private_mode,
                user_text=prompt_text,
                reply_to_telegram_message_id=reply_to_message_id,
                reply_fallback_text=reply_fallback,
            )

            assistant_msg_id = 0
            if store_enabled:
                user_msg_id = await storage.create_message(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    message_thread_id=thread_id,
                    telegram_message_id=telegram_message_id,
                    role="user",
                    text=prompt_text,
                    reply_to_telegram_message_id=reply_to_message_id,
                )
                if telegram_message_id is not None:
                    try:
                        await storage.add_topic_message_id(
                            user_id=message.from_user.id,
                            chat_id=message.chat.id,
                            message_thread_id=thread_id,
                            telegram_message_id=int(telegram_message_id),
                            owner="user",
                        )
                    except Exception:
                        pass
                assistant_msg_id = await storage.create_message(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    message_thread_id=thread_id,
                    role="assistant",
                    text="",
                    parent_id=user_msg_id,
                )
                asyncio.create_task(_maybe_enqueue_nlp(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=thread_id, lang_code=lang))

            await ctx_message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
            await _stream_to_chat(
                ctx_message,
                copilot,
                composed,
                lang,
                user_id=message.from_user.id,
                storage=storage,
                assistant_message_id=assistant_msg_id,
                show_duration=show_duration,
                store_enabled=store_enabled,
                enable_actions=store_enabled,
            )

        defaults = await storage.get_user_settings(message.from_user.id)
        await storage.ensure_thread_settings(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_thread_id=thread_id,
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        tset = await storage.get_thread_settings(user_id=message.from_user.id, chat_id=message.chat.id, message_thread_id=thread_id)
        if not bool(tset.get("asked_private_mode", False)):
            await storage.set_pending_topic_message(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                telegram_message_id=message.message_id,
                text=user_text,
                reply_to_telegram_message_id=reply_to_id,
                reply_fallback_text=reply_fallback_text,
            )
            await storage.update_thread_settings(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                asked_private_mode=True,
            )
            await _send_markdown_v2_message_api(
                message.bot,
                chat_id=message.chat.id,
                message_thread_id=thread_id,
                text=t(lang, "private_prompt"),
                reply_markup=_kb_private_prompt(lang),
            )
            return

        await _process_prompt(
            ctx_message=message,
            telegram_message_id=message.message_id,
            prompt_text=user_text,
            reply_to_message_id=reply_to_id,
            reply_fallback=reply_fallback_text,
        )

    @router.callback_query(F.data.startswith("topic_priv:"))
    async def topic_private_mode_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message is None:
            return
        lang = _lang_for(callback.from_user.id)
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        choice = (callback.data or "").split(":", 1)[-1].strip().lower()
        enable = True if choice == "on" else False
        await storage.update_thread_settings(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            private_mode=enable,
            asked_private_mode=True,
        )
        pending = await storage.get_pending_topic_message(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        await storage.clear_pending_topic_message(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        await _edit_or_send(callback=callback, text=t(lang, "settings_text"), reply_markup=_kb_help(lang))
        if not pending:
            return

        user_text = str(pending.get("text") or "").strip()
        if not user_text:
            return
        reply_to_id = pending.get("reply_to_telegram_message_id")
        reply_fallback_text = str(pending.get("reply_fallback_text") or "")
        telegram_message_id = pending.get("telegram_message_id")

        defaults = await storage.get_user_settings(callback.from_user.id)
        await storage.ensure_thread_settings(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            default_show_duration=bool(defaults.get("show_duration", True)),
            default_response_mode=str(defaults.get("response_mode", "normal")),
        )
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        show_duration = bool(tset.get("show_duration", True))
        response_mode = str(tset.get("response_mode", "normal"))
        private_mode = bool(tset.get("private_mode", False))
        store_enabled = not private_mode

        composed = await _compose_prompt(
            storage=storage,
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            current_thread_id=thread_id,
            response_mode=response_mode,
            private_mode=private_mode,
            user_text=user_text,
            reply_to_telegram_message_id=int(reply_to_id) if reply_to_id is not None else None,
            reply_fallback_text=reply_fallback_text,
        )

        assistant_msg_id = 0
        if store_enabled:
            user_msg_id = await storage.create_message(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                telegram_message_id=int(telegram_message_id) if telegram_message_id is not None else None,
                role="user",
                text=user_text,
                reply_to_telegram_message_id=int(reply_to_id) if reply_to_id is not None else None,
            )
            if telegram_message_id is not None:
                try:
                    await storage.add_topic_message_id(
                        user_id=callback.from_user.id,
                        chat_id=callback.message.chat.id,
                        message_thread_id=thread_id,
                        telegram_message_id=int(telegram_message_id),
                        owner="user",
                    )
                except Exception:
                    pass
            assistant_msg_id = await storage.create_message(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                message_thread_id=thread_id,
                role="assistant",
                text="",
                parent_id=user_msg_id,
            )
            asyncio.create_task(_maybe_enqueue_nlp(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id, lang_code=lang))

        await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
        await _stream_to_chat(
            callback.message,
            copilot,
            composed,
            lang,
            user_id=callback.from_user.id,
            storage=storage,
            assistant_message_id=assistant_msg_id,
            show_duration=show_duration,
            store_enabled=store_enabled,
            enable_actions=store_enabled,
        )

    @router.callback_query(F.data.startswith("noop:"))
    async def noop_handler(callback: CallbackQuery) -> None:
        await callback.answer()

    @router.callback_query(F.data.startswith("sum:"))
    async def summarize_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        lang = user_lang.get(callback.from_user.id, "en")
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        if not verified_users.get(callback.from_user.id, False):
            await _send_message_api(callback.bot, chat_id=callback.message.chat.id, message_thread_id=thread_id, text=t(lang, "join_required"), reply_markup=kb_join(lang))
            return
        raw_id = (callback.data or "").split(":", 1)[-1]
        try:
            target_id = int(raw_id)
        except Exception:
            return
        target = await storage.get_message(target_id)
        if not target or target.user_id != callback.from_user.id:
            return
        parent = await storage.get_parent(target_id)
        user_part = parent.text if parent else ""

        prompt = (
            f"Language: {lang}\n"
            "Write the reply in the given language.\n\n"
            "Summarize the assistant answer in a concise way.\n"
            "Reply with the summary only.\n\n"
            f"User message:\n{user_part}\n\n"
            f"Assistant answer:\n{target.text}"
        )
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        show_duration = bool(tset.get("show_duration", True))
        response_mode = str(tset.get("response_mode", "normal"))
        composed = await _compose_prompt(
            storage=storage,
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            current_thread_id=thread_id,
            response_mode=response_mode,
            private_mode=False,
            user_text=prompt,
            reply_to_telegram_message_id=None,
            reply_fallback_text="",
        )
        action_user_id = await storage.create_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            role="user",
            text="[summarize]",
            parent_id=target_id,
        )
        assistant_id = await storage.create_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            role="assistant",
            text="",
            parent_id=action_user_id,
        )
        await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
        await _stream_to_chat(
            callback.message,
            copilot,
            composed,
            lang,
            user_id=callback.from_user.id,
            storage=storage,
            assistant_message_id=assistant_id,
            show_duration=show_duration,
            store_enabled=True,
            enable_actions=True,
        )

    @router.callback_query(F.data.startswith("exp:"))
    async def explain_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        lang = user_lang.get(callback.from_user.id, "en")
        thread_id = getattr(callback.message, "message_thread_id", None) if callback.message else None
        if not verified_users.get(callback.from_user.id, False):
            await _send_message_api(callback.bot, chat_id=callback.message.chat.id, message_thread_id=thread_id, text=t(lang, "join_required"), reply_markup=kb_join(lang))
            return
        raw_id = (callback.data or "").split(":", 1)[-1]
        try:
            target_id = int(raw_id)
        except Exception:
            return
        target = await storage.get_message(target_id)
        if not target or target.user_id != callback.from_user.id:
            return
        parent = await storage.get_parent(target_id)
        user_part = parent.text if parent else ""

        prompt = (
            f"Language: {lang}\n"
            "Write the reply in the given language.\n\n"
            "Explain the assistant answer in more detail.\n"
            "Reply with the expanded answer only.\n\n"
            f"User message:\n{user_part}\n\n"
            f"Assistant answer:\n{target.text}"
        )
        tset = await storage.get_thread_settings(user_id=callback.from_user.id, chat_id=callback.message.chat.id, message_thread_id=thread_id)
        show_duration = bool(tset.get("show_duration", True))
        response_mode = str(tset.get("response_mode", "normal"))
        composed = await _compose_prompt(
            storage=storage,
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            current_thread_id=thread_id,
            response_mode=response_mode,
            private_mode=False,
            user_text=prompt,
            reply_to_telegram_message_id=None,
            reply_fallback_text="",
        )
        action_user_id = await storage.create_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            role="user",
            text="[explain_more]",
            parent_id=target_id,
        )
        assistant_id = await storage.create_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_thread_id=thread_id,
            role="assistant",
            text="",
            parent_id=action_user_id,
        )
        await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
        await _stream_to_chat(
            callback.message,
            copilot,
            composed,
            lang,
            user_id=callback.from_user.id,
            storage=storage,
            assistant_message_id=assistant_id,
            show_duration=show_duration,
            store_enabled=True,
            enable_actions=True,
        )

    dp = Dispatcher()
    dp.include_router(router)
    return dp

async def run_bot() -> None:
    config = load_config()
    bot = Bot(token=config.bot_token)
    base_copilot = CopilotClient()
    user_pool = _StreamWorkerPool(workers=config.user_llm_workers, max_queue_size=config.llm_queue_size)
    nlp_pool = _StreamWorkerPool(workers=config.nlp_llm_workers, max_queue_size=config.llm_queue_size)
    user_pool.start()
    nlp_pool.start()
    copilot = QueuedCopilotClient(base_copilot, user_pool=user_pool, nlp_pool=nlp_pool)
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot.db"))
    storage = Storage(db_path=db_path)
    dp = build_dispatcher(copilot, storage)


    await bot.set_my_commands(COMMANDS_BY_LANG["en"])
    for lang_code, cmds in COMMANDS_BY_LANG.items():
        if lang_code == "en":
            continue
        await bot.set_my_commands(cmds, language_code=lang_code)

    try:
        await dp.start_polling(bot)
    finally:
        await user_pool.aclose()
        await nlp_pool.aclose()
