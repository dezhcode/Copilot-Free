import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import requests
import websockets


@dataclass(frozen=True)
class CopilotSession:
    conversation_id: str
    cookie: str


class CopilotClient:
    def __init__(self) -> None:
        self._user_agent = "CopilotNative/30.0.430320002 (Android 9; samsung; SM-G988N)"
        self._system_prompt = (
            "Reply with the answer only.\n"
            "Use Telegram MarkdownV2.\n"
            "You may use: *bold*, _italic_, `inline code`, ```code blocks```, and bullet lists.\n"
            "No preface, no meta, no explanations about formatting."
        )

    def _language_name(self, language: str) -> str:
        language = (language or "").strip().lower()
        return {
            "fa": "Persian",
            "en": "English",
            "ru": "Russian",
            "ar": "Arabic",
        }.get(language, "English")

    def _build_prompt(self, user_text: str, language: str) -> str:
        user_text = (user_text or "").strip()
        return f"{self._system_prompt}\nWrite in {self._language_name(language)}.\n\n{user_text}"

    async def ask(self, user_text: str, language: str = "en") -> str:
        final_text = ""
        async for delta in self.ask_stream(user_text, language=language):
            final_text += delta
        return final_text.strip() or " "

    async def ask_stream(self, user_text: str, language: str = "en") -> AsyncIterator[str]:
        prompt = self._build_prompt(user_text, language=language)
        session = await self._start_conversation()
        async for delta in self._chat_stream(user_text=prompt, session=session):
            yield delta

    async def _start_conversation(self) -> CopilotSession:
        url = "https://copilot.microsoft.com/c/api/start"
        payload = {
            "timeZone": "Asia/Tehran",
            "startNewConversation": True,
            "teenSupportEnabled": False,
        }
        headers = {
            "User-Agent": self._user_agent,
            "x-search-uilang": "en-US",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

        def _req() -> requests.Response:
            return requests.post(url, json=payload, headers=headers, timeout=15)

        resp = await asyncio.to_thread(_req)
        resp.raise_for_status()
        data = resp.json()
        conversation_id = data.get("currentConversationId")
        cookie = resp.headers.get("set-cookie", "")

        if not conversation_id or not cookie:
            raise RuntimeError("Copilot start failed")

        return CopilotSession(conversation_id=conversation_id, cookie=cookie)

    async def _chat_stream(self, user_text: str, session: CopilotSession) -> AsyncIterator[str]:
        ws_url = "wss://copilot.microsoft.com/c/api/chat?api-version=2"
        headers = {"User-Agent": self._user_agent, "Cookie": session.cookie}

        last_error: Optional[Exception] = None
        for attempt in range(3):
            yielded_any = False
            try:
                try:
                    ws_cm = websockets.connect(ws_url, additional_headers=headers)
                except TypeError:
                    ws_cm = websockets.connect(ws_url, extra_headers=headers)
                async with ws_cm as ws:
                    await ws.send(
                        json.dumps(
                            {
                                "event": "setOptions",
                                "supportedCards": [],
                                "supportedActions": [],
                            }
                        )
                    )
                    await ws.send(
                        json.dumps(
                            {
                                "event": "send",
                                "content": [{"type": "text", "text": user_text}],
                                "context": {},
                                "conversationId": session.conversation_id,
                            }
                        )
                    )

                    while True:
                        raw = await asyncio.wait_for(ws.recv(), timeout=45)
                        data = json.loads(raw)
                        if data.get("event") == "appendText" and data.get("text"):
                            yielded_any = True
                            yield data["text"]
                        elif data.get("event") == "done":
                            return
            except Exception as e:
                last_error = e
                if yielded_any:
                    break
                await asyncio.sleep(0.5 * (attempt + 1))

        raise last_error or RuntimeError("Copilot chat failed")
