import unittest

from codex_bot.constants import BOT_ID, OTHER_BOT_ID
from codex_bot.conversation import (
    InvalidHistoryError,
    conversacion_terminada,
    debo_anunciar_despedida,
    debo_cerrar,
    es_mi_turno,
    siguiente_bot,
    siguiente_id,
    validar_historial,
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
        rows = [
            make_row(index, OTHER_BOT_ID if index % 2 else BOT_ID)
            for index in range(1, 17)
        ]

        self.assertTrue(conversacion_terminada(rows))
        self.assertFalse(es_mi_turno(rows, BOT_ID))

    def test_fila_15_anuncia_despedida_y_fila_16_cierra(self) -> None:
        fourteen_rows = self.make_valid_history(14)
        fifteen_rows = self.make_valid_history(15)

        self.assertTrue(debo_anunciar_despedida(fourteen_rows, OTHER_BOT_ID))
        self.assertFalse(debo_cerrar(fourteen_rows, BOT_ID))
        self.assertTrue(debo_cerrar(fifteen_rows, BOT_ID))

    def test_valida_historial_vacio(self) -> None:
        validar_historial([])

    def test_valida_historial_con_alternancia_estricta(self) -> None:
        validar_historial(self.make_valid_history(4))

    def test_rechaza_ids_con_huecos(self) -> None:
        rows = [make_row(1, OTHER_BOT_ID), make_row(3, BOT_ID)]

        with self.assertRaisesRegex(InvalidHistoryError, "ID inválido"):
            validar_historial(rows)

    def test_rechaza_ids_duplicados(self) -> None:
        rows = [make_row(1, OTHER_BOT_ID), make_row(1, BOT_ID)]

        with self.assertRaisesRegex(InvalidHistoryError, "ID inválido"):
            validar_historial(rows)

    def test_rechaza_bots_desconocidos(self) -> None:
        rows = [make_row(1, "otro_bot")]

        with self.assertRaisesRegex(InvalidHistoryError, "Bot desconocido"):
            validar_historial(rows)

    def test_rechaza_alternancia_invalida(self) -> None:
        rows = [make_row(1, OTHER_BOT_ID), make_row(2, OTHER_BOT_ID)]

        with self.assertRaisesRegex(InvalidHistoryError, "Alternancia inválida"):
            validar_historial(rows)

    def test_rechaza_historico_mayor_a_16_filas(self) -> None:
        rows = self.make_valid_history(16) + [make_row(17, OTHER_BOT_ID)]

        with self.assertRaisesRegex(InvalidHistoryError, "máximo es 16"):
            validar_historial(rows)

    def test_rechaza_timestamp_con_formato_invalido(self) -> None:
        row = ChatRow(1, OTHER_BOT_ID, "Hola", "2026-08-03 12:00:00")

        with self.assertRaisesRegex(InvalidHistoryError, "Timestamp inválido"):
            validar_historial([row])

    def test_rechaza_timestamp_con_fecha_inexistente(self) -> None:
        row = ChatRow(1, OTHER_BOT_ID, "Hola", "2026-02-30T12:00:00Z")

        with self.assertRaisesRegex(InvalidHistoryError, "fecha u hora inexistente"):
            validar_historial([row])

    def test_rechaza_mensaje_mayor_al_limite(self) -> None:
        row = ChatRow(1, OTHER_BOT_ID, "a" * 501, "2026-08-03T12:00:00Z")

        with self.assertRaisesRegex(InvalidHistoryError, "Mensaje inválido"):
            validar_historial([row])

    def test_calcula_el_siguiente_bot_por_paridad(self) -> None:
        self.assertEqual(siguiente_bot([]), OTHER_BOT_ID)
        self.assertEqual(siguiente_bot(self.make_valid_history(1)), BOT_ID)

    def test_rechaza_identidad_local_desconocida(self) -> None:
        with self.assertRaises(ValueError):
            es_mi_turno([], "desconocido")

    @staticmethod
    def make_valid_history(length: int) -> list[ChatRow]:
        return [
            make_row(index, OTHER_BOT_ID if index % 2 else BOT_ID)
            for index in range(1, length + 1)
        ]
