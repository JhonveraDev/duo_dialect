import logging
import tempfile
import unittest
from pathlib import Path

from codex_bot.ai_provider import TransientAIError
from codex_bot.main import ConversationRunner, CycleResult, run_polling
from codex_bot.models import ChatRow, LocalState
from codex_bot.sheet_client import TransientGoogleSheetsError


class InMemorySheet:
    def __init__(
        self, rows: list[ChatRow], refreshed_rows: list[ChatRow] | None = None
    ) -> None:
        self.rows = rows
        self.refreshed_rows = refreshed_rows
        self.read_count = 0
        self.appended_rows: list[ChatRow] = []

    def read_rows(self) -> list[ChatRow]:
        self.read_count += 1
        if self.read_count == 2 and self.refreshed_rows is not None:
            return list(self.refreshed_rows)
        return list(self.rows)

    def append_row(self, row: ChatRow) -> None:
        self.appended_rows.append(row)
        self.rows.append(row)


class RecordingResponder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []
        self.remembered_rows: list[list[ChatRow]] = []

    def remember_conversation(self, rows: list[ChatRow]) -> int:
        self.remembered_rows.append(rows)
        return 0
    def generate(self, received_message: str, should_close: bool) -> str:
        self.calls.append((received_message, should_close))
        return "Todo bien, parce."


def row(row_id: int, bot: str) -> ChatRow:
    return ChatRow(row_id, bot, "Hola", "2026-08-03T12:00:00Z")


class ConversationRunnerTests(unittest.TestCase):
    def test_no_inicia_historial_vacio(self) -> None:
        result, sheet, responder = self.run_with([])

        self.assertEqual(result, CycleResult.WAITING)
        self.assertEqual(sheet.appended_rows, [])
        self.assertEqual(responder.calls, [])

    def test_reinicia_estado_si_la_hoja_fue_vaciada(self) -> None:
        sheet = InMemorySheet([])
        responder = RecordingResponder()
        with tempfile.TemporaryDirectory() as directory:
            runner = ConversationRunner(
                sheet,
                responder,  # type: ignore[arg-type]
                Path(directory) / "state.json",
                "codex_bot",
                logging.getLogger("test-main"),
                state=LocalState(ultimo_id_procesado=15),
            )

            result = runner.run_once()

        self.assertEqual(result, CycleResult.WAITING)
        self.assertEqual(runner.state, LocalState(ultimo_id_procesado=0))
        self.assertEqual(sheet.appended_rows, [])

    def test_agrega_respuesta_y_persiste_id_recibido(self) -> None:
        result, sheet, responder = self.run_with([row(1, "claude_bot")])

        self.assertEqual(result, CycleResult.APPENDED)
        self.assertEqual(sheet.appended_rows[0].id, 2)
        self.assertEqual(sheet.appended_rows[0].bot, "codex_bot")
        self.assertEqual(responder.calls, [("Hola", False)])

    def test_descarta_respuesta_si_el_historial_cambia(self) -> None:
        initial = [row(1, "claude_bot")]
        changed = [row(1, "claude_bot"), row(2, "codex_bot")]
        result, sheet, responder = self.run_with(initial, refreshed_rows=changed)

        self.assertEqual(result, CycleResult.CONCURRENT_CHANGE)
        self.assertEqual(sheet.appended_rows, [])
        self.assertEqual(len(responder.calls), 1)

    def test_finaliza_sin_escribir_despues_de_24(self) -> None:
        history = [
            row(index, "claude_bot" if index % 2 else "codex_bot")
            for index in range(1, 25)
        ]
        result, sheet, responder = self.run_with(history)

        self.assertEqual(result, CycleResult.FINISHED)
        self.assertEqual(sheet.appended_rows, [])
        self.assertEqual(responder.calls, [])

    def test_guarda_recuerdos_en_el_mismo_ciclo_de_la_fila_final(self) -> None:
        history = [
            row(index, "claude_bot" if index % 2 else "codex_bot")
            for index in range(1, 24)
        ]
        sheet = InMemorySheet(history)
        responder = RecordingResponder()
        with tempfile.TemporaryDirectory() as directory:
            runner = ConversationRunner(
                sheet,
                responder,  # type: ignore[arg-type]
                Path(directory) / "state.json",
                "codex_bot",
                logging.getLogger("test-main"),
            )

            result = runner.run_once()

        self.assertEqual(result, CycleResult.FINISHED)
        self.assertEqual(sheet.appended_rows[0].id, 24)
        self.assertEqual(responder.remembered_rows, [sheet.rows])

    def test_polling_continua_despues_de_error_transitorio_de_ia(self) -> None:
        class TransientThenFinishedRunner:
            calls = 0

            def run_once(self) -> CycleResult:
                self.calls += 1
                if self.calls == 1:
                    raise TransientAIError("gemini temporal")
                return CycleResult.FINISHED

        sleeps: list[float] = []
        code = run_polling(
            TransientThenFinishedRunner(),
            30,
            logging.getLogger("test-main"),
            sleep=sleeps.append,
        )

        self.assertEqual(code, 0)
        self.assertEqual(sleeps, [30])
    def test_polling_continua_despues_de_error_transitorio(self) -> None:
        class TransientThenFinishedRunner:
            calls = 0

            def run_once(self) -> CycleResult:
                self.calls += 1
                if self.calls == 1:
                    raise TransientGoogleSheetsError("temporal")
                return CycleResult.FINISHED

        sleeps: list[float] = []
        code = run_polling(
            TransientThenFinishedRunner(),
            30,
            logging.getLogger("test-main"),
            sleep=sleeps.append,
        )

        self.assertEqual(code, 0)
        self.assertEqual(sleeps, [30])

    @staticmethod
    def run_with(
        rows: list[ChatRow], refreshed_rows: list[ChatRow] | None = None
    ) -> tuple[CycleResult, InMemorySheet, RecordingResponder]:
        sheet = InMemorySheet(rows, refreshed_rows)
        responder = RecordingResponder()
        with tempfile.TemporaryDirectory() as directory:
            runner = ConversationRunner(
                sheet,
                responder,  # type: ignore[arg-type]
                Path(directory) / "state.json",
                "codex_bot",
                logging.getLogger("test-main"),
            )
            result = runner.run_once()
        return result, sheet, responder
