import json
import unittest

from codex_bot.web_lookup import PublicWebLookupProvider


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def read(self) -> bytes:
        return self._body


class WebLookupTests(unittest.TestCase):
    def test_consulta_general_devuelve_resumen_y_fuente(self) -> None:
        def opener(request: object, timeout: float) -> FakeResponse:
            del request, timeout
            return FakeResponse(
                json.dumps(
                    {
                        "AbstractText": "Bogotá es la capital de Colombia.",
                        "AbstractSource": "Wikipedia",
                        "AbstractURL": "https://es.wikipedia.org/wiki/Bogotá",
                    }
                ).encode()
            )

        result = PublicWebLookupProvider(opener).lookup("capital de Colombia")

        self.assertIn("Bogotá", result.summary)
        self.assertEqual(result.sources[0].title, "Wikipedia")
        self.assertIn("FUENTES WEB", result.as_prompt_context())

    def test_consulta_de_noticias_prioriza_el_feed_de_actualidad(self) -> None:
        def opener(request: object, timeout: float) -> FakeResponse:
            del timeout
            self.assertIn("news.google.com", request.full_url)
            return FakeResponse(
                b"<rss><channel><item><title>Noticia de prueba</title>"
                b"<link>https://example.test/noticia</link>"
                b"<pubDate>Mon, 17 Aug 2026 12:00:00 GMT</pubDate>"
                b"</item></channel></rss>"
            )

        result = PublicWebLookupProvider(opener).lookup("noticias de hoy")

        self.assertEqual(result.summary, "Noticia de prueba")
        self.assertEqual(result.sources[0].title, "Google News")


if __name__ == "__main__":
    unittest.main()