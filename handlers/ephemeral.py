from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

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
    track: bool = True,
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
    logger.info(
        "sendMessage(receiver_user_id=%s) -> %r",
        receiver_user_id,
        result,
    )
    if not isinstance(result, dict):
        return None
    emid = result.get("ephemeral_message_id")
    if isinstance(emid, int):
        if track:
            pending[(chat_id, receiver_user_id)] = emid
        return emid
    logger.warning(
        "sendMessage returned no ephemeral_message_id; keys=%s",
        list(result.keys()),
    )
    return None


async def reply_ephemeral(message: Message, text: str) -> None:
    # Bot's reply to an admin command, visible only to the actor.
    # Falls back to a public reply if ephemeral isn't available
    # (private chats, non-supergroups, missing bot permissions).
    bot = message.bot
    user_id = message.from_user.id if message.from_user else None
    if bot is None or user_id is None:
        await message.reply(text)
        return
    emid = await send_ephemeral(
        bot, message.chat.id, user_id, text, track=False,
    )
    if emid is None:
        await message.reply(text)


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
