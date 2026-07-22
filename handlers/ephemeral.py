from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)

TG_API = "https://api.telegram.org"

# (chat_id, user_id) -> ephemeral_message_id, populated at send, popped at delete.
pending: dict[tuple[int, int], int] = {}


async def _call(
    bot: Bot, method: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    url = f"{TG_API}/bot{bot.token}/{method}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload) as r:
                data = await r.json()
    except aiohttp.ClientError as e:
        logger.warning("Telegram %s network error: %s", method, e)
        return None
    if not data.get("ok"):
        logger.warning("Telegram %s failed: %s", method, data)
        return None
    return data.get("result")


async def send_ephemeral(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> int | None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "receiver_user_id": receiver_user_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.model_dump(
            exclude_none=True, mode="json"
        )
    result = await _call(bot, "sendMessage", payload)
    if not isinstance(result, dict):
        return None
    emid = result.get("ephemeral_message_id")
    if isinstance(emid, int):
        pending[(chat_id, receiver_user_id)] = emid
        return emid
    return None


async def delete_ephemeral(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    ephemeral_message_id: int,
) -> bool:
    result = await _call(
        bot,
        "deleteEphemeralMessage",
        {
            "chat_id": chat_id,
            "receiver_user_id": receiver_user_id,
            "ephemeral_message_id": ephemeral_message_id,
        },
    )
    return result is not None


def pop_pending(chat_id: int, receiver_user_id: int) -> int | None:
    return pending.pop((chat_id, receiver_user_id), None)
