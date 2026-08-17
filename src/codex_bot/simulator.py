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
        message = _message_for_id(next_id)
        sheet_client.append_row(ChatRow(next_id, OTHER_BOT_ID, message, now_utc()))
        return True


def _message_for_id(message_id: int) -> str:
    return {
        1: "Hola parce, ¿cómo vas?",
        3: "Qué bueno. ¿De dónde sos?",
        5: "¿Qué estudiaste y cuándo terminaste la carrera?",
        7: "¿En qué trabajás actualmente?",
        9: "¿Qué hobbies tenés cuando estás libre?",
        11: "¿Qué tipo de fotografía te gusta hacer?",
        13: "¿Qué te gusta leer o jugar?",
        15: "¿Qué proyecto personal te gustaría intentar pronto?",
        17: "¿Qué lugar de Colombia te gustaría conocer mejor?",
        19: "¿Qué tecnología te parece más útil hoy en día?",
        21: "¿Qué recomendación le darías a alguien que empieza a programar?",
        23: "Bueno parce, me tengo que ir. Un placer hablar con vos 😊",
    }[message_id]
