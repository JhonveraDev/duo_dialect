import tempfile
import unittest
from pathlib import Path

from codex_bot.knowledge import KnowledgeError, load_knowledge


class KnowledgeTests(unittest.TestCase):
    def test_carga_archivo_completo_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("##HOBBIES\n- Fotografía 📷", encoding="utf-8")

            self.assertEqual(load_knowledge(path), "##HOBBIES\n- Fotografía 📷")

    def test_rechaza_archivo_vacio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("  \n", encoding="utf-8")

            with self.assertRaisesRegex(KnowledgeError, "vacía"):
                load_knowledge(path)
