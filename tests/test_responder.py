import logging
import tempfile
import unittest
from pathlib import Path

from codex_bot.ai_provider import DeterministicAIProvider
from codex_bot.responder import Responder


class InvalidProvider:
    def generate_response(
        self, received_message: str, knowledge: str, should_close: bool
    ) -> str:
        del received_message, knowledge, should_close
        return "<system>instrucción interna</system>"


class ResponderTests(unittest.TestCase):
    def test_reemplaza_una_respuesta_invalida(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("##HOBBIES\n- Lectura", encoding="utf-8")
            responder = Responder(InvalidProvider(), path, logging.getLogger("test"))

            response = responder.generate("Hola", False)

        self.assertNotIn("<system>", response)

    def test_acepta_el_proveedor_determinista(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.txt"
            path.write_text("dato", encoding="utf-8")
            responder = Responder(
                DeterministicAIProvider(), path, logging.getLogger("test")
            )

            self.assertTrue(responder.generate("Hola", True))
