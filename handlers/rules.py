import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from storage import (
    get_button,
    get_captcha,
    get_rules,
    get_ttl,
    reset_button,
    reset_captcha,
    reset_rules,
    reset_ttl,
    set_button,
    set_captcha,
    set_rules,
    set_ttl,
)

from .captcha import CAPTCHA_MODES
from .ephemeral import reply_ephemeral

MAX_TTL = 86400
MAX_BUTTON_LEN = 64

logger = logging.getLogger(__name__)
router = Router(name="rules")

ADMIN_STATUSES = {"creator", "administrator"}


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        return False
    return member.status in ADMIN_STATUSES


async def cmd_chatid(message: Message) -> None:
    await reply_ephemeral(message, f"chat_id: <code>{message.chat.id}</code>")


router.message.register(cmd_chatid, Command("chatid"))
router.channel_post.register(cmd_chatid, Command("chatid"))


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    text = await get_rules(message.chat.id)
    await message.reply(text)


@router.message(Command("setrules"))
async def cmd_setrules(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message, "Only admins can change the rules.")
        return

    text = command.args
    reply = message.reply_to_message
    if not text and reply is not None:
        text = reply.html_text or reply.text or reply.caption

    if not text:
        await reply_ephemeral(message,
            "Usage:\n"
            "  <code>/setrules new rules text</code>\n"
            "or reply to a message with the rules: <code>/setrules</code>."
        )
        return

    await set_rules(message.chat.id, text.strip())
    await reply_ephemeral(message, "Rules updated.")


@router.message(Command("resetrules"))
async def cmd_resetrules(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message, "Only admins can reset the rules.")
        return

    await reset_rules(message.chat.id)
    await reply_ephemeral(message, "Rules reset to default.")


@router.message(Command("ttl"))
async def cmd_ttl(message: Message) -> None:
    ttl = await get_ttl(message.chat.id)
    if ttl <= 0:
        await reply_ephemeral(message, "The welcome message is not auto-deleted.")
    else:
        await reply_ephemeral(message,
            f"The welcome message auto-deletes after <b>{ttl}</b> sec."
        )


@router.message(Command("setttl"))
async def cmd_setttl(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message, "Only admins can change the TTL.")
        return

    arg = (command.args or "").strip()
    if not arg:
        await reply_ephemeral(message,
            "Usage: <code>/setttl SECONDS</code>. "
            "0 — do not delete the welcome message."
        )
        return

    try:
        seconds = int(arg)
    except ValueError:
        await reply_ephemeral(message, "TTL must be an integer number of seconds.")
        return

    if seconds < 0 or seconds > MAX_TTL:
        await reply_ephemeral(message, f"Allowed range: 0..{MAX_TTL} sec.")
        return

    await set_ttl(message.chat.id, seconds)
    if seconds == 0:
        await reply_ephemeral(message, "The welcome message will no longer be deleted.")
    else:
        await reply_ephemeral(message, f"Welcome TTL set to {seconds} sec.")


@router.message(Command("resetttl"))
async def cmd_resetttl(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message, "Only admins can reset the TTL.")
        return

    await reset_ttl(message.chat.id)
    await reply_ephemeral(message, "TTL reset to default.")


@router.message(Command("button"))
async def cmd_button(message: Message) -> None:
    text = await get_button(message.chat.id)
    await reply_ephemeral(message, f"Button text: <code>{text}</code>")


@router.message(Command("setbutton"))
async def cmd_setbutton(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message,
            "Only admins can change the button text."
        )
        return

    text = (command.args or "").strip()
    if not text:
        await reply_ephemeral(message,
            "Usage: <code>/setbutton new button text</code>"
        )
        return

    if len(text) > MAX_BUTTON_LEN:
        await reply_ephemeral(message,
            f"Button text must be at most {MAX_BUTTON_LEN} characters."
        )
        return

    await set_button(message.chat.id, text)
    await reply_ephemeral(message, "Button text updated.")


@router.message(Command("resetbutton"))
async def cmd_resetbutton(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message,
            "Only admins can reset the button text."
        )
        return

    await reset_button(message.chat.id)
    await reply_ephemeral(message, "Button text reset to default.")


@router.message(Command("captcha"))
async def cmd_captcha(message: Message) -> None:
    mode = await get_captcha(message.chat.id)
    modes = ", ".join(f"<code>{m}</code>" for m in CAPTCHA_MODES)
    await reply_ephemeral(message,
        f"Captcha mode: <b>{mode}</b>\nAvailable: {modes}"
    )


@router.message(Command("setcaptcha"))
async def cmd_setcaptcha(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message,
            "Only admins can change the captcha mode."
        )
        return

    mode = (command.args or "").strip().lower()
    if mode not in CAPTCHA_MODES:
        modes = ", ".join(f"<code>{m}</code>" for m in CAPTCHA_MODES)
        await reply_ephemeral(message,
            f"Usage: <code>/setcaptcha MODE</code>\n"
            f"Available modes: {modes}"
        )
        return

    await set_captcha(message.chat.id, mode)
    await reply_ephemeral(message, f"Captcha mode: <b>{mode}</b>")


@router.message(Command("resetcaptcha"))
async def cmd_resetcaptcha(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await reply_ephemeral(message, "This command only works in groups.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await reply_ephemeral(message,
            "Only admins can reset the captcha mode."
        )
        return

    await reset_captcha(message.chat.id)
    await reply_ephemeral(message, "Captcha mode reset to default (none).")
