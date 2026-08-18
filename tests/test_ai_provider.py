import unittest

from codex_bot.ai_provider import (
    AnthropicAIProvider,
    DeterministicAIProvider,
    TransientAIError,
    run_with_ai_backoff,
)
from codex_bot.validator import validate_response


class DeterministicAIProviderTests(unittest.TestCase):
    def test_produce_respuestas_validas_y_deterministas(self) -> None:
        provider = DeterministicAIProvider()

        response = provider.generate_response("¿Dónde vivís?", "##INFO\n- dato", False)

        self.assertTrue(validate_response(response, "dato").valid)
        self.assertEqual(
            response,
            provider.generate_response("¿Dónde vivís?", "dato", False),
        )

    def test_no_inventa_recuerdos_en_modo_sin_api(self) -> None:
        provider = DeterministicAIProvider()

        self.assertEqual(provider.extract_memories([], "dato", []), [])
class TemporaryGeminiError(Exception):
    def __str__(self) -> str:
        return "503 UNAVAILABLE"


class AIBackoffTests(unittest.TestCase):
    def test_reintenta_503_y_luego_devuelve_la_respuesta(self) -> None:
        attempts = 0
        sleeps: list[float] = []

        def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TemporaryGeminiError()
            return "ok"

        self.assertEqual(run_with_ai_backoff(operation, sleep=sleeps.append), "ok")
        self.assertEqual(sleeps, [1, 2])

    def test_reporta_error_transitorio_despues_de_cinco_intentos(self) -> None:
        with self.assertRaises(TransientAIError):
            run_with_ai_backoff(
                lambda: (_ for _ in ()).throw(TemporaryGeminiError()),
                sleep=lambda _: None,
            )

class FakeMessages:
    def __init__(self) -> None:
        self.arguments: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.arguments = kwargs
        text_block = type("TextBlock", (), {"type": "text", "text": "Todo bien."})()
        return type("Response", (), {"content": [text_block]})()


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


class AnthropicAIProviderTests(unittest.TestCase):
    def test_envia_prompt_restrictivo_sin_llamada_real(self) -> None:
        client = FakeAnthropicClient()
        provider = AnthropicAIProvider("clave-falsa", "modelo-prueba", client)

        response = provider.generate_response("¿Qué hacés?", "##HOBBIES\n- Leer", False)

        self.assertEqual(response, "Todo bien.")
        assert client.messages.arguments is not None
        self.assertEqual(client.messages.arguments["model"], "modelo-prueba")
        self.assertEqual(client.messages.arguments["max_tokens"], 2000)
        self.assertIn("únicamente", str(client.messages.arguments["system"]))
