"""Reglas puras para decidir el estado de la conversación."""

import re
from collections.abc import Sequence
from datetime import datetime

from codex_bot.constants import (
    ALLOWED_BOT_IDS,
    BOT_ID,
    FAREWELL_ANNOUNCEMENT_ID,
    FINAL_MESSAGE_ID,
    MESSAGE_LIMIT,
    OTHER_BOT_ID,
)
from codex_bot.models import ChatRow

UTC_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class InvalidHistoryError(ValueError):
    """El historial compartido incumple el contrato de interoperabilidad."""


def validar_historial(rows: Sequence[ChatRow]) -> None:
    """Verifica invariantes del contrato sin producir efectos secundarios.

    Un historial vacío es válido porque claude_bot es quien debe iniciarlo. Las
    filas existentes deben tener una secuencia completa y alternar desde
    claude_bot en el identificador 1.
    """
    if len(rows) > MESSAGE_LIMIT:
        raise InvalidHistoryError(
            f"El historial tiene {len(rows)} filas; el máximo es {MESSAGE_LIMIT}."
        )

    for expected_id, row in enumerate(rows, start=1):
        if row.id != expected_id:
            raise InvalidHistoryError(
                f"ID inválido: se esperaba {expected_id} y se recibió {row.id}."
            )
        if row.bot not in ALLOWED_BOT_IDS:
            raise InvalidHistoryError(f"Bot desconocido: {row.bot!r}.")

        expected_bot = OTHER_BOT_ID if row.id % 2 else BOT_ID
        if row.bot != expected_bot:
            raise InvalidHistoryError(
                f"Alternancia inválida en ID {row.id}: se esperaba {expected_bot}."
            )
        if not isinstance(row.mensaje, str) or len(row.mensaje) > 500:
            raise InvalidHistoryError(
                f"Mensaje inválido en ID {row.id}: supera 500 caracteres o no es texto."
            )
        _validar_timestamp(row.timestamp, row.id)


def _validar_timestamp(timestamp: str, row_id: int) -> None:
    if not isinstance(timestamp, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(timestamp):
        raise InvalidHistoryError(
            f"Timestamp inválido en ID {row_id}; se requiere YYYY-MM-DDTHH:MM:SSZ."
        )
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise InvalidHistoryError(
            f"Timestamp inválido en ID {row_id}; fecha u hora inexistente."
        ) from error


def siguiente_bot(rows: Sequence[ChatRow]) -> str:
    """Devuelve la identidad que debe escribir el siguiente mensaje válido."""
    return OTHER_BOT_ID if siguiente_id(rows) % 2 else BOT_ID


def conversacion_terminada(rows: Sequence[ChatRow]) -> bool:
    """Indica si ya se alcanzó el límite contractual de mensajes."""
    return len(rows) >= MESSAGE_LIMIT


def siguiente_id(rows: Sequence[ChatRow]) -> int:
    """Devuelve el identificador de la próxima fila si el historial es válido."""
    return len(rows) + 1


def es_mi_turno(rows: Sequence[ChatRow], mi_bot_id: str = BOT_ID) -> bool:
    """Determina el turno sin acceder a red, disco ni estado global."""
    if mi_bot_id not in ALLOWED_BOT_IDS:
        raise ValueError(f"Identidad de bot no permitida: {mi_bot_id!r}.")
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
    return mi_bot_id == OTHER_BOT_ID and siguiente_id(rows) == FAREWELL_ANNOUNCEMENT_ID
