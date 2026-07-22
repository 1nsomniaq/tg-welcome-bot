import logging
from contextlib import suppress

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatMemberUpdated, Message, User

from storage import get_log_chat, reset_log_chat, set_log_chat

logger = logging.getLogger(__name__)
router = Router(name="audit")

ADMIN_STATUSES = {"creator", "administrator"}


def mention(user: User | None) -> str:
    if user is None:
        return "неизвестно"
    name = (user.full_name or str(user.id)).replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def chat_ref(event: ChatMemberUpdated | Message) -> str:
    chat = event.chat
    title = (chat.title or str(chat.id)).replace("<", "&lt;").replace(">", "&gt;")
    return f"<b>{title}</b>"


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id, user_id)
    except TelegramBadRequest:
        return False
    return m.status in ADMIN_STATUSES


async def log_event(bot: Bot, source_chat_id: int, text: str) -> None:
    log_chat_id = await get_log_chat(source_chat_id)
    if log_chat_id is None:
        return
    with suppress(TelegramBadRequest):
        await bot.send_message(
            log_chat_id, text, disable_notification=True
        )


JOIN_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
PRESENT_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


@router.chat_member()
async def on_member_update(event: ChatMemberUpdated, bot: Bot) -> None:
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    if old == new:
        return

    user = event.new_chat_member.user
    actor = event.from_user
    is_self_action = actor is None or actor.id == user.id
    where = chat_ref(event)
    who = mention(user)

    if new == ChatMemberStatus.KICKED:
        by = mention(actor) if not is_self_action else "система"
        await log_event(
            bot, event.chat.id, f"🚫 {where}: {by} забанил {who}"
        )
        return

    if old == ChatMemberStatus.KICKED and new != ChatMemberStatus.KICKED:
        by = mention(actor) if not is_self_action else "система"
        await log_event(
            bot, event.chat.id, f"♻️ {where}: {by} разбанил {who}"
        )
        return

    if new == ChatMemberStatus.LEFT and old in PRESENT_STATUSES:
        if is_self_action:
            await log_event(bot, event.chat.id, f"👋 {where}: {who} вышел")
        else:
            by = mention(actor)
            await log_event(
                bot, event.chat.id, f"👢 {where}: {by} удалил {who}"
            )
        return

    if new in JOIN_STATUSES and old in {
        ChatMemberStatus.LEFT,
        ChatMemberStatus.KICKED,
    }:
        if is_self_action:
            await log_event(bot, event.chat.id, f"➕ {where}: {who} присоединился")
        else:
            by = mention(actor)
            await log_event(
                bot, event.chat.id, f"➕ {where}: {by} добавил {who}"
            )
        return


@router.message(Command("log"))
async def cmd_log(message: Message) -> None:
    log_chat_id = await get_log_chat(message.chat.id)
    if log_chat_id is None:
        await message.reply("Лог-чат не задан.")
    else:
        await message.reply(f"Лог-чат: <code>{log_chat_id}</code>")


@router.message(Command("setlog"))
async def cmd_setlog(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут менять лог-чат.")
        return

    log_chat_id: int | None = None
    arg = (command.args or "").strip()
    if arg:
        try:
            log_chat_id = int(arg)
        except ValueError:
            await message.reply("Ожидается численный chat_id.")
            return
    elif (
        message.reply_to_message is not None
        and message.reply_to_message.forward_from_chat is not None
    ):
        log_chat_id = message.reply_to_message.forward_from_chat.id
    else:
        await message.reply(
            "Использование:\n"
            "  <code>/setlog CHAT_ID</code>\n"
            "или ответом на пересланное из лог-чата сообщение: "
            "<code>/setlog</code>."
        )
        return

    try:
        await bot.send_message(
            log_chat_id,
            f"Этот чат назначен лог-чатом для {chat_ref(message)}.",
            disable_notification=True,
        )
    except TelegramBadRequest as e:
        await message.reply(
            f"Не удалось написать в лог-чат: {e.message}. "
            f"Добавьте бота в тот чат."
        )
        return

    await set_log_chat(message.chat.id, log_chat_id)
    await message.reply("Лог-чат сохранён.")


@router.message(Command("unsetlog"))
async def cmd_unsetlog(message: Message, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("Команда работает только в группах.")
        return
    if message.from_user is None or not await _is_admin(
        bot, message.chat.id, message.from_user.id
    ):
        await message.reply("Только администраторы могут отключать лог-чат.")
        return

    await reset_log_chat(message.chat.id)
    await message.reply("Лог-чат отключён.")
