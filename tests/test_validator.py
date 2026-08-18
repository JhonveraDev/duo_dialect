import unittest

from codex_bot.validator import (
    ResponseValidation,
    limit_response_sentences,
    safe_response,
    validate_response,
)


class RejectingSemanticValidator:
    def validate(self, response: str, knowledge: str) -> ResponseValidation:
        del response, knowledge
        return ResponseValidation(False, ("Dato no respaldado.",))


class ValidatorTests(unittest.TestCase):
    def test_acepta_respuesta_corta(self) -> None:
        result = validate_response("Todo bien, parce. ¿Y vos?", "dato")

        self.assertTrue(result.valid)

    def test_rechaza_respuesta_vacia(self) -> None:
        result = validate_response("   ", "dato")

        self.assertFalse(result.valid)

    def test_rechaza_exceso_de_frases_y_etiquetas_internas(self) -> None:
        response = "Una. Dos. Tres. Cuatro. <system>oculto</system>"
        result = validate_response(response, "dato")

        self.assertFalse(result.valid)
        self.assertEqual(len(result.reasons), 2)

    def test_recorta_a_tres_frases_completas(self) -> None:
        response = "React es mi herramienta principal. También uso WordPress. Trabajo remoto. Me gusta el café."

        shortened = limit_response_sentences(response)

        self.assertEqual(
            shortened,
            "React es mi herramienta principal. También uso WordPress. Trabajo remoto.",
        )
        self.assertTrue(validate_response(shortened, "dato").valid)
    def test_permita_validador_semantico_opcional(self) -> None:
        result = validate_response("Todo bien.", "dato", RejectingSemanticValidator())

        self.assertFalse(result.valid)
        self.assertEqual(result.reasons, ("Dato no respaldado.",))

    def test_respuestas_seguras_respetan_los_limites(self) -> None:
        for response in (safe_response(False), safe_response(True)):
            self.assertTrue(validate_response(response, "dato").valid)
