"""Constantes del contrato de interoperabilidad."""

from typing import Final

BOT_ID: Final[str] = "codex_bot"
OTHER_BOT_ID: Final[str] = "claude_bot"
ALLOWED_BOT_IDS: Final[frozenset[str]] = frozenset({BOT_ID, OTHER_BOT_ID})
SHEET_NAME: Final[str] = "chat"
SHEET_HEADER: Final[tuple[str, str, str, str]] = (
    "id",
    "bot",
    "mensaje",
    "timestamp",
)
MESSAGE_LIMIT: Final[int] = 16
FAREWELL_ANNOUNCEMENT_ID: Final[int] = 15
FINAL_MESSAGE_ID: Final[int] = 16
MAX_MESSAGE_LENGTH: Final[int] = 500
