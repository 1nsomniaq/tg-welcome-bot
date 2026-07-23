from __future__ import annotations

import random
from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CAPTCHA_MODES = ("none", "math", "emoji")
DEFAULT_CAPTCHA = "none"

EMOJI_POOL = [
    "🐱", "🐶", "🌸", "🎂", "🍕", "🚀",
    "🍎", "⚽", "🎧", "🌙", "🔥", "🍀",
]


@dataclass
class Challenge:
    text: str  # extra question line, appended to welcome; empty if unused
    keyboard: InlineKeyboardMarkup


def build(
    mode: str,
    chat_id: int,
    user_id: int,
    agree_prefix: str,
    button_text: str,
) -> Challenge:
    if mode == "math":
        return _math(chat_id, user_id, agree_prefix)
    if mode == "emoji":
        return _emoji(chat_id, user_id, agree_prefix)
    return _plain(chat_id, user_id, agree_prefix, button_text)


def _cb(agree_prefix: str, chat_id: int, user_id: int, correct: bool) -> str:
    return f"{agree_prefix}:{chat_id}:{user_id}:{1 if correct else 0}"


def _plain(
    chat_id: int, user_id: int, agree_prefix: str, button_text: str
) -> Challenge:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=_cb(agree_prefix, chat_id, user_id, True),
                )
            ]
        ]
    )
    return Challenge(text="", keyboard=kb)


def _math(chat_id: int, user_id: int, agree_prefix: str) -> Challenge:
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    op = random.choice(["+", "−"])
    if op == "−" and b > a:
        a, b = b, a
    correct = a + b if op == "+" else a - b

    wrongs: set[int] = set()
    while len(wrongs) < 3:
        candidate = correct + random.randint(-5, 5)
        if candidate != correct and candidate >= 0:
            wrongs.add(candidate)

    options = list(wrongs) + [correct]
    random.shuffle(options)

    buttons = [
        InlineKeyboardButton(
            text=str(opt),
            callback_data=_cb(agree_prefix, chat_id, user_id, opt == correct),
        )
        for opt in options
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons[:2], buttons[2:]])
    text = f"🧮 Solve to accept the rules: <b>{a} {op} {b} = ?</b>"
    return Challenge(text=text, keyboard=kb)


def _emoji(chat_id: int, user_id: int, agree_prefix: str) -> Challenge:
    options = random.sample(EMOJI_POOL, 6)
    correct = random.choice(options)
    buttons = [
        InlineKeyboardButton(
            text=e,
            callback_data=_cb(agree_prefix, chat_id, user_id, e == correct),
        )
        for e in options
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons[:3], buttons[3:]])
    text = f"🧩 Tap <b>{correct}</b> to accept the rules."
    return Challenge(text=text, keyboard=kb)
