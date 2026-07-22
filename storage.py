from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from config import BUTTON_TEXT, RULES_TEXT, settings

_PATH = Path(__file__).parent / "chats.json"
_lock = asyncio.Lock()


def _read() -> dict[str, dict[str, Any]]:
    if not _PATH.exists():
        return {}
    try:
        raw = json.loads(_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def _write(data: dict[str, dict[str, Any]]) -> None:
    _PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _entry(data: dict[str, dict[str, Any]], chat_id: int) -> dict[str, Any]:
    return data.setdefault(str(chat_id), {})


async def get_rules(chat_id: int) -> str:
    async with _lock:
        return _read().get(str(chat_id), {}).get("rules", RULES_TEXT)


async def set_rules(chat_id: int, text: str) -> None:
    async with _lock:
        data = _read()
        _entry(data, chat_id)["rules"] = text
        _write(data)


async def reset_rules(chat_id: int) -> None:
    async with _lock:
        data = _read()
        entry = data.get(str(chat_id))
        if entry is not None:
            entry.pop("rules", None)
            if not entry:
                data.pop(str(chat_id), None)
        _write(data)


async def get_ttl(chat_id: int) -> int:
    async with _lock:
        return _read().get(str(chat_id), {}).get("ttl", settings.welcome_ttl)


async def set_ttl(chat_id: int, seconds: int) -> None:
    async with _lock:
        data = _read()
        _entry(data, chat_id)["ttl"] = seconds
        _write(data)


async def reset_ttl(chat_id: int) -> None:
    async with _lock:
        data = _read()
        entry = data.get(str(chat_id))
        if entry is not None:
            entry.pop("ttl", None)
            if not entry:
                data.pop(str(chat_id), None)
        _write(data)


async def get_button(chat_id: int) -> str:
    async with _lock:
        return _read().get(str(chat_id), {}).get("button", BUTTON_TEXT)


async def set_button(chat_id: int, text: str) -> None:
    async with _lock:
        data = _read()
        _entry(data, chat_id)["button"] = text
        _write(data)


async def reset_button(chat_id: int) -> None:
    async with _lock:
        data = _read()
        entry = data.get(str(chat_id))
        if entry is not None:
            entry.pop("button", None)
            if not entry:
                data.pop(str(chat_id), None)
        _write(data)


async def get_log_chat(chat_id: int) -> int | None:
    async with _lock:
        raw = _read().get(str(chat_id), {}).get("log_chat")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            try:
                return int(raw)
            except ValueError:
                return None
        return None


async def set_log_chat(chat_id: int, log_chat_id: int) -> None:
    async with _lock:
        data = _read()
        _entry(data, chat_id)["log_chat"] = log_chat_id
        _write(data)


async def reset_log_chat(chat_id: int) -> None:
    async with _lock:
        data = _read()
        entry = data.get(str(chat_id))
        if entry is not None:
            entry.pop("log_chat", None)
            if not entry:
                data.pop(str(chat_id), None)
        _write(data)


async def get_captcha(chat_id: int) -> str:
    async with _lock:
        raw = _read().get(str(chat_id), {}).get("captcha")
        if isinstance(raw, str):
            return raw
        return "none"


async def set_captcha(chat_id: int, mode: str) -> None:
    async with _lock:
        data = _read()
        _entry(data, chat_id)["captcha"] = mode
        _write(data)


async def reset_captcha(chat_id: int) -> None:
    async with _lock:
        data = _read()
        entry = data.get(str(chat_id))
        if entry is not None:
            entry.pop("captcha", None)
            if not entry:
                data.pop(str(chat_id), None)
        _write(data)
