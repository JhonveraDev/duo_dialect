import tempfile
import unittest
from pathlib import Path

from codex_bot.knowledge import KnowledgeError, knowledge_backed_response, load_knowledge


class KnowledgeTests(unittest.TestCase):
    def test_carga_archivo_completo_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("##HOBBIES\n- Fotografía 📷", encoding="utf-8")

            self.assertEqual(load_knowledge(path), "##HOBBIES\n- Fotografía 📷")

    def test_la_alternativa_usa_el_dato_relacionado_a_la_pregunta(self) -> None:
        knowledge = (
            "##TRABAJO\n"
            "- Trabajo actual: Actualmente trabajo independiente en proyectos web.\n"
            "- Hobbies: Me gusta el rock."
        )

        response = knowledge_backed_response("¿En qué trabajás?", knowledge, False)

        self.assertIn("trabajo independiente", response)
        self.assertNotIn("Uy, de eso", response)
    def test_rechaza_archivo_vacio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("  \n", encoding="utf-8")

            with self.assertRaisesRegex(KnowledgeError, "vacía"):
                load_knowledge(path)
