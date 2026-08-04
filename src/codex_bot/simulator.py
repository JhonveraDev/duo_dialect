"""Simulador determinista de claude_bot para pruebas del contrato."""

from codex_bot.constants import OTHER_BOT_ID
from codex_bot.conversation import (
    conversacion_terminada,
    siguiente_id,
    validar_historial,
)
from codex_bot.models import ChatRow
from codex_bot.sheet_client import SheetClient, now_utc


class ClaudeBotSimulator:
    """Escribe los turnos impares de claude_bot de forma determinista."""

    def run_once(self, sheet_client: SheetClient) -> bool:
        """Añade como máximo una fila de claude_bot y devuelve si escribió."""
        rows = sheet_client.read_rows()
        validar_historial(rows)
        if conversacion_terminada(rows):
            return False
        if rows and rows[-1].bot != "codex_bot":
            return False
        next_id = siguiente_id(rows)
        if next_id % 2 == 0:
            return False
        message = (
            "Bueno parce, me tengo que ir. Un placer hablar con vos 😊"
            if next_id == 15
            else "Hola parce, ¿cómo vas?"
        )
        sheet_client.append_row(ChatRow(next_id, OTHER_BOT_ID, message, now_utc()))
        return True
