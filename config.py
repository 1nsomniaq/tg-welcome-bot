import os
from dataclasses import dataclass


BUTTON_TEXT = "✅ I agree to the rules"

RULES_TEXT = """<b>Правила чата</b>

1. Уважайте других участников.
2. Никакого спама и рекламы.
3. Обсуждаем только темы, связанные с чатом.
4. За нарушения — мут или бан.

Нажмите кнопку ниже, чтобы подтвердить, что вы прочитали и принимаете правила."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    welcome_ttl: int


def _load() -> Settings:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var is required")
    return Settings(
        bot_token=token,
        welcome_ttl=int(os.environ.get("WELCOME_TTL", "300")),
    )


settings = _load()
