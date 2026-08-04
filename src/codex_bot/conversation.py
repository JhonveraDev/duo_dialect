"""Reglas puras para decidir el estado de la conversación."""

from collections.abc import Sequence

from codex_bot.constants import (
    BOT_ID,
    FAREWELL_ANNOUNCEMENT_ID,
    FINAL_MESSAGE_ID,
    MESSAGE_LIMIT,
    OTHER_BOT_ID,
)
from codex_bot.models import ChatRow


def conversacion_terminada(rows: Sequence[ChatRow]) -> bool:
    """Indica si ya se alcanzó el límite contractual de mensajes."""
    return len(rows) >= MESSAGE_LIMIT


def siguiente_id(rows: Sequence[ChatRow]) -> int:
    """Devuelve el identificador de la próxima fila si el historial es válido."""
    return len(rows) + 1


def es_mi_turno(rows: Sequence[ChatRow], mi_bot_id: str = BOT_ID) -> bool:
    """Determina el turno sin acceder a red, disco ni estado global."""
    if conversacion_terminada(rows):
        return False
    if not rows:
        return mi_bot_id == OTHER_BOT_ID
    return rows[-1].bot != mi_bot_id


def debo_cerrar(rows: Sequence[ChatRow], mi_bot_id: str = BOT_ID) -> bool:
    """Indica si el bot debe cerrar al redactar la fila 16."""
    return mi_bot_id == BOT_ID and siguiente_id(rows) == FINAL_MESSAGE_ID


def debo_anunciar_despedida(rows: Sequence[ChatRow], mi_bot_id: str) -> bool:
    """Indica si claude_bot debe anunciar la despedida en la fila 15."""
    return (
        mi_bot_id == OTHER_BOT_ID
        and siguiente_id(rows) == FAREWELL_ANNOUNCEMENT_ID
    )

