import logging
import tempfile
import unittest
from pathlib import Path

from codex_bot.ai_provider import DeterministicAIProvider
from codex_bot.fake_sheet import FakeSheetClient
from codex_bot.main import ConversationRunner, CycleResult
from codex_bot.responder import Responder
from codex_bot.simulator import ClaudeBotSimulator
from codex_bot.validator import validate_response


class FakeIntegrationTests(unittest.TestCase):
    def test_conversacion_completa_tiene_16_filas_validas(self) -> None:
        sheet = FakeSheetClient()
        simulator = ClaudeBotSimulator()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            knowledge_path = root / "knowledge.txt"
            knowledge_path.write_text("##HOBBIES\n- Lectura", encoding="utf-8")
            responder = Responder(
                DeterministicAIProvider(), knowledge_path, logging.getLogger("test-e2e")
            )
            runner = ConversationRunner(
                sheet,
                responder,
                root / "state.json",
                "codex_bot",
                logging.getLogger("test-e2e"),
            )

            while len(sheet.read_rows()) < 16:
                simulator.run_once(sheet)
                result = runner.run_once()
                if len(sheet.read_rows()) < 16:
                    self.assertEqual(result, CycleResult.APPENDED)

        rows = sheet.read_rows()
        self.assertEqual([row.id for row in rows], list(range(1, 17)))
        self.assertEqual([row.bot for row in rows[::2]], ["claude_bot"] * 8)
        self.assertEqual([row.bot for row in rows[1::2]], ["codex_bot"] * 8)
        self.assertEqual(rows[-1].bot, "codex_bot")
        self.assertIn("me tengo que ir", rows[14].mensaje)
        self.assertTrue(all(len(row.mensaje) <= 500 for row in rows))
        self.assertTrue(
            all(validate_response(row.mensaje, "dato").valid for row in rows)
        )
        self.assertFalse(simulator.run_once(sheet))
        self.assertEqual(runner.run_once(), CycleResult.FINISHED)
