import tempfile
import unittest
from pathlib import Path

from codex_bot.config import ConfigError, Settings


class ConfigTests(unittest.TestCase):
    def test_crea_configuracion_fake_valida(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            knowledge = root / "knowledge.txt"
            knowledge.write_text("##HOBBIES\n- Leer", encoding="utf-8")

            settings = Settings.from_environment(self.environment(knowledge))

        self.assertEqual(settings.bot_id, "codex_bot")
        self.assertEqual(settings.poll_interval_seconds, 30)

    def test_rechaza_bot_id_distinto(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            knowledge = Path(directory) / "knowledge.txt"
            knowledge.write_text("dato", encoding="utf-8")
            environment = self.environment(knowledge) | {"BOT_ID": "claude_bot"}

            with self.assertRaisesRegex(ConfigError, "BOT_ID"):
                Settings.from_environment(environment)

    def test_rechaza_limite_distinto_de_16(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            knowledge = Path(directory) / "knowledge.txt"
            knowledge.write_text("dato", encoding="utf-8")
            environment = self.environment(knowledge) | {"LIMITE_MENSAJES": "15"}

            with self.assertRaisesRegex(ConfigError, "LIMITE_MENSAJES"):
                Settings.from_environment(environment)

    def test_exige_credenciales_en_ejecucion_real(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            knowledge = root / "knowledge.txt"
            knowledge.write_text("dato", encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "GOOGLE_CREDENTIALS_PATH"):
                Settings.from_environment(
                    self.environment(knowledge), require_credentials=True
                )

    @staticmethod
    def environment(knowledge: Path) -> dict[str, str]:
        return {
            "GOOGLE_SHEET_ID": "sheet-id",
            "GOOGLE_CREDENTIALS_PATH": "missing-credentials.json",
            "BOT_ID": "codex_bot",
            "INTERVALO_LECTURA": "30",
            "LIMITE_MENSAJES": "16",
            "AI_PROVIDER": "fake",
            "LOG_LEVEL": "INFO",
            "KNOWLEDGE_FILE": str(knowledge),
        }
