import unittest
from pathlib import Path

from codex_bot.models import ChatRow
from codex_bot.web_server import WebConfigError, messages_payload, port_from_environment


class WebServerTests(unittest.TestCase):
    def test_serializa_las_filas_sin_exponer_otros_datos(self) -> None:
        payload = messages_payload(
            [ChatRow(1, "claude_bot", "Hola", "2026-08-17T20:00:00Z")]
        )

        self.assertEqual(
            payload,
            {
                "messages": [
                    {
                        "id": 1,
                        "bot": "claude_bot",
                        "mensaje": "Hola",
                        "timestamp": "2026-08-17T20:00:00Z",
                    }
                ]
            },
        )

    def test_acepta_puerto_configurado(self) -> None:
        self.assertEqual(port_from_environment({"CHAT_UI_PORT": "8081"}), 8081)

    def test_rechaza_puerto_fuera_de_rango(self) -> None:
        with self.assertRaises(WebConfigError):
            port_from_environment({"CHAT_UI_PORT": "70000"})


if __name__ == "__main__":
    unittest.main()