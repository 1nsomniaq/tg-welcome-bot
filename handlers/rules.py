import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from storage import (
    get_button,
    get_rules,
    get_ttl,
    reset_button,
    reset_rules,
    reset_ttl,
    set_button,
    set_rules,
    set_ttl,
)

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


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    text = await get_rules(message.chat.id)
    await message.reply(text)


@router.message(Command("setrules"))
async def cmd_setrules(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут менять правила.")
        return

    text = command.args
    reply = message.reply_to_message
    if not text and reply is not None:
        text = reply.html_text or reply.text or reply.caption

    if not text:
        await message.reply(
            "Использование:\n"
            "  <code>/setrules новый текст правил</code>\n"
            "или ответом на сообщение с правилами: <code>/setrules</code>."
        )
        return

    await set_rules(message.chat.id, text.strip())
    await message.reply("Правила обновлены.")


@router.message(Command("resetrules"))
async def cmd_resetrules(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут сбрасывать правила.")
        return

    await reset_rules(message.chat.id)
    await message.reply("Правила сброшены к значению по умолчанию.")


@router.message(Command("ttl"))
async def cmd_ttl(message: Message) -> None:
    ttl = await get_ttl(message.chat.id)
    if ttl <= 0:
        await message.reply("Приветствие сейчас не удаляется автоматически.")
    else:
        await message.reply(
            f"Приветствие автоудаляется через <b>{ttl}</b> сек."
        )


@router.message(Command("setttl"))
async def cmd_setttl(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут менять TTL.")
        return

    arg = (command.args or "").strip()
    if not arg:
        await message.reply(
            "Использование: <code>/setttl СЕКУНДЫ</code>. "
            "0 — не удалять приветствие."
        )
        return

    try:
        seconds = int(arg)
    except ValueError:
        await message.reply("TTL должен быть целым числом секунд.")
        return

    if seconds < 0 or seconds > MAX_TTL:
        await message.reply(f"Допустимый диапазон: 0..{MAX_TTL} сек.")
        return

    await set_ttl(message.chat.id, seconds)
    if seconds == 0:
        await message.reply("Приветствие больше не будет удаляться.")
    else:
        await message.reply(f"TTL приветствия установлен: {seconds} сек.")


@router.message(Command("resetttl"))
async def cmd_resetttl(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут сбрасывать TTL.")
        return

    await reset_ttl(message.chat.id)
    await message.reply("TTL сброшен к значению по умолчанию.")


@router.message(Command("button"))
async def cmd_button(message: Message) -> None:
    text = await get_button(message.chat.id)
    await message.reply(f"Текст кнопки: <code>{text}</code>")


@router.message(Command("setbutton"))
async def cmd_setbutton(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply(
            "Только администраторы могут менять текст кнопки."
        )
        return

    text = (command.args or "").strip()
    if not text:
        await message.reply(
            "Использование: <code>/setbutton новый текст кнопки</code>"
        )
        return

    if len(text) > MAX_BUTTON_LEN:
        await message.reply(
            f"Текст кнопки не должен быть длиннее {MAX_BUTTON_LEN} символов."
        )
        return

    await set_button(message.chat.id, text)
    await message.reply("Текст кнопки обновлён.")


@router.message(Command("resetbutton"))
async def cmd_resetbutton(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply(
            "Только администраторы могут сбрасывать текст кнопки."
        )
        return

    await reset_button(message.chat.id)
    await message.reply("Текст кнопки сброшен к значению по умолчанию.")
