from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.chat_member_updated import (
    JOIN_TRANSITION,
    ChatMemberUpdatedFilter,
)
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    User,
)

from storage import get_button, get_captcha, get_rules, get_ttl

from . import captcha
from .audit import log_event, mention
from .ephemeral import delete_ephemeral, pop_pending, send_ephemeral

logger = logging.getLogger(__name__)
router = Router(name="welcome")

AGREE_PREFIX = "rules_agree"

# (chat_id, user_id) of members still waiting to press the button.
# Populated at send time; removed on click or on kick.
waiting: set[tuple[int, int]] = set()

MUTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
)

UNMUTED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
    can_pin_messages=False,
    can_change_info=False,
)


def _mention(user_id: int, name: str) -> str:
    safe = name.replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user_id}">{safe}</a>'


async def _kick(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        await bot.ban_chat_member(chat_id, user_id)
    except TelegramBadRequest as e:
        logger.warning("ban_chat_member failed: %s", e)
        return False
    with suppress(TelegramBadRequest):
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    return True


async def _expire_ephemeral(
    bot: Bot,
    chat_id: int,
    user: User,
    emid: int,
    ttl: int,
) -> None:
    await asyncio.sleep(ttl)
    user_id = user.id
    key = (chat_id, user_id)
    if key not in waiting:
        return
    waiting.discard(key)
    pop_pending(chat_id, user_id)
    await delete_ephemeral(bot, chat_id, user_id, emid)
    if await _kick(bot, chat_id, user_id):
        await log_event(
            bot,
            chat_id,
            f"👢 {mention(user)} didn't accept the rules within {ttl} sec — kicked",
        )


async def _expire_visible(
    bot: Bot,
    chat_id: int,
    user: User,
    message_id: int,
    ttl: int,
) -> None:
    await asyncio.sleep(ttl)
    user_id = user.id
    key = (chat_id, user_id)
    if key not in waiting:
        return
    waiting.discard(key)
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id, message_id)
    if await _kick(bot, chat_id, user_id):
        await log_event(
            bot,
            chat_id,
            f"👢 {mention(user)} didn't accept the rules within {ttl} sec — kicked",
        )


@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
async def on_join(event: ChatMemberUpdated, bot: Bot) -> None:
    user = event.new_chat_member.user
    if user.is_bot:
        return

    chat_id = event.chat.id
    user_id = user.id

    if event.chat.type != "supergroup":
        logger.warning(
            "Chat %s is %r, not supergroup — restrict_chat_member won't work",
            chat_id,
            event.chat.type,
        )

    with suppress(TelegramBadRequest):
        await bot.restrict_chat_member(
            chat_id, user_id, permissions=MUTED
        )

    rules = await get_rules(chat_id)
    button_text = await get_button(chat_id)
    ttl = await get_ttl(chat_id)
    mode = await get_captcha(chat_id)
    challenge = captcha.build(
        mode, chat_id, user_id, AGREE_PREFIX, button_text
    )
    prompt = f"\n\n{challenge.text}" if challenge.text else ""
    # Use @username for an actual notification ping; fall back to a
    # text_mention link when the user has no public username.
    if user.username:
        greeting = f"Hi, @{user.username}!"
    else:
        greeting = f"Hi, {_mention(user_id, user.full_name)}!"
    text = f"{greeting}\n\n{rules}{prompt}"
    keyboard = challenge.keyboard

    waiting.add((chat_id, user_id))

    emid = await send_ephemeral(bot, chat_id, user_id, text, keyboard)
    if emid is not None:
        if ttl > 0:
            asyncio.create_task(
                _expire_ephemeral(bot, chat_id, user, emid, ttl)
            )
    else:
        logger.info(
            "Ephemeral send failed for user %s in chat %s, falling back",
            user_id,
            chat_id,
        )
        msg = await bot.send_message(chat_id, text, reply_markup=keyboard)
        if ttl > 0:
            asyncio.create_task(
                _expire_visible(bot, chat_id, user, msg.message_id, ttl)
            )

    actor = event.from_user
    if actor is not None and actor.id != user_id:
        await log_event(
            bot,
            chat_id,
            f"➕ {mention(actor)} added {mention(user)} (waiting for rules acceptance)",
        )
    else:
        await log_event(
            bot,
            chat_id,
            f"➕ {mention(user)} joined (waiting for rules acceptance)",
        )


@router.callback_query(F.data.startswith(f"{AGREE_PREFIX}:"))
async def on_agree(call: CallbackQuery, bot: Bot) -> None:
    parts = (call.data or "").split(":")
    if len(parts) != 4:
        await call.answer("Invalid button", show_alert=True)
        return
    try:
        chat_id = int(parts[1])
        target_id = int(parts[2])
        correct = parts[3] == "1"
    except ValueError:
        await call.answer("Invalid button", show_alert=True)
        return

    if call.from_user.id != target_id:
        await call.answer("This button is not for you.", show_alert=True)
        return

    if not correct:
        await call.answer(
            "❌ Wrong, try again.", show_alert=True
        )
        return

    waiting.discard((chat_id, target_id))

    with suppress(TelegramBadRequest):
        await bot.restrict_chat_member(
            chat_id, target_id, permissions=UNMUTED
        )

    emid = pop_pending(chat_id, target_id)
    if emid is not None:
        await delete_ephemeral(bot, chat_id, target_id, emid)
    elif call.message is not None:
        with suppress(TelegramBadRequest):
            await bot.delete_message(chat_id, call.message.message_id)

    await call.answer("Welcome!")

    await log_event(
        bot,
        chat_id,
        f"✅ {mention(call.from_user)} accepted the rules",
    )
