import unittest

from codex_bot.constants import BOT_ID, OTHER_BOT_ID
from codex_bot.conversation import (
    conversacion_terminada,
    debo_anunciar_despedida,
    debo_cerrar,
    es_mi_turno,
    siguiente_id,
)
from codex_bot.models import ChatRow


def make_row(row_id: int, bot: str) -> ChatRow:
    return ChatRow(
        id=row_id,
        bot=bot,
        mensaje="Hola",
        timestamp="2026-08-03T12:00:00Z",
    )


class ConversationTests(unittest.TestCase):
    def test_codex_bot_no_inicia_un_historial_vacio(self) -> None:
        self.assertFalse(es_mi_turno([], BOT_ID))
        self.assertTrue(es_mi_turno([], OTHER_BOT_ID))

    def test_el_turno_depende_de_la_ultima_fila(self) -> None:
        claude_row = make_row(1, OTHER_BOT_ID)
        codex_row = make_row(2, BOT_ID)

        self.assertTrue(es_mi_turno([claude_row], BOT_ID))
        self.assertFalse(es_mi_turno([codex_row], BOT_ID))

    def test_calcula_siguiente_id_por_el_total_de_filas(self) -> None:
        rows = [make_row(1, OTHER_BOT_ID), make_row(2, BOT_ID)]

        self.assertEqual(siguiente_id(rows), 3)

    def test_detecta_fin_al_llegar_a_16_filas(self) -> None:
        rows = [make_row(index, OTHER_BOT_ID) for index in range(1, 17)]

        self.assertTrue(conversacion_terminada(rows))
        self.assertFalse(es_mi_turno(rows, BOT_ID))

    def test_fila_15_anuncia_despedida_y_fila_16_cierra(self) -> None:
        fourteen_rows = [make_row(index, OTHER_BOT_ID) for index in range(1, 15)]
        fifteen_rows = [make_row(index, OTHER_BOT_ID) for index in range(1, 16)]

        self.assertTrue(debo_anunciar_despedida(fourteen_rows, OTHER_BOT_ID))
        self.assertFalse(debo_cerrar(fourteen_rows, BOT_ID))
        self.assertTrue(debo_cerrar(fifteen_rows, BOT_ID))
