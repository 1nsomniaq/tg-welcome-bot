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
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from storage import get_button, get_rules, get_ttl

from .audit import log_event, mention

logger = logging.getLogger(__name__)
router = Router(name="welcome")

AGREE_PREFIX = "rules_agree"

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


def _agree_keyboard(user_id: int, button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"{AGREE_PREFIX}:{user_id}",
                )
            ]
        ]
    )


def _mention(user_id: int, name: str) -> str:
    safe = name.replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user_id}">{safe}</a>'


async def _expire_welcome(
    bot: Bot, chat_id: int, message_id: int, ttl: int
) -> None:
    await asyncio.sleep(ttl)
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id, message_id)


@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
async def on_join(event: ChatMemberUpdated, bot: Bot) -> None:
    user = event.new_chat_member.user
    if user.is_bot:
        return

    chat_id = event.chat.id
    user_id = user.id

    with suppress(TelegramBadRequest):
        await bot.restrict_chat_member(
            chat_id, user_id, permissions=MUTED
        )

    rules = await get_rules(chat_id)
    button_text = await get_button(chat_id)
    text = f"Привет, {_mention(user_id, user.full_name)}!\n\n{rules}"
    msg = await bot.send_message(
        chat_id,
        text,
        reply_markup=_agree_keyboard(user_id, button_text),
    )

    ttl = await get_ttl(chat_id)
    if ttl > 0:
        asyncio.create_task(
            _expire_welcome(bot, chat_id, msg.message_id, ttl)
        )

    actor = event.from_user
    if actor is not None and actor.id != user_id:
        await log_event(
            bot,
            chat_id,
            f"➕ {mention(actor)} добавил {mention(user)} (ждём согласия с правилами)",
        )
    else:
        await log_event(
            bot,
            chat_id,
            f"➕ {mention(user)} присоединился (ждём согласия с правилами)",
        )


@router.callback_query(F.data.startswith(f"{AGREE_PREFIX}:"))
async def on_agree(call: CallbackQuery, bot: Bot) -> None:
    _, _, target_str = call.data.partition(":")
    try:
        target_id = int(target_str)
    except ValueError:
        await call.answer("Некорректная кнопка", show_alert=True)
        return

    if call.from_user.id != target_id:
        await call.answer("Эта кнопка не для вас.", show_alert=True)
        return

    if call.message is None:
        await call.answer()
        return

    chat_id = call.message.chat.id
    with suppress(TelegramBadRequest):
        await bot.restrict_chat_member(
            chat_id, target_id, permissions=UNMUTED
        )
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id, call.message.message_id)

    await call.answer("Добро пожаловать!")

    await log_event(
        bot,
        chat_id,
        f"✅ {mention(call.from_user)} принял правила",
    )
