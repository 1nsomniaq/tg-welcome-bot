import os
from dataclasses import dataclass


BUTTON_TEXT = "✅ I agree to the rules"

RULES_TEXT = """<b>Chat rules</b>

1. Respect other members.
2. No spam or advertising.
3. Stay on topic.
4. Violations result in mute or ban.

Tap the button below to confirm you've read and accept the rules."""


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
