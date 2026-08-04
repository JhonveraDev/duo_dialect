import unittest

from codex_bot.ai_provider import AnthropicAIProvider, DeterministicAIProvider
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
