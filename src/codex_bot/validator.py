"""Validación defensiva de las respuestas antes de enviarlas al Sheet."""

import re
from dataclasses import dataclass
from typing import Protocol

from codex_bot.constants import MAX_MESSAGE_LENGTH

SENTENCE_ENDING_PATTERN = re.compile(r"[.!?]+")
INTERNAL_CONTENT_PATTERN = re.compile(
    r"<[^>]+>|\b(?:system|prompt|instrucciones\s+internas)\s*:", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class ResponseValidation:
    """Resultado de las reglas sintácticas y opcionalmente semánticas."""

    valid: bool
    reasons: tuple[str, ...] = ()


class SemanticValidator(Protocol):
    """Extensión opcional para validar afirmaciones frente al conocimiento."""

    def validate(self, response: str, knowledge: str) -> ResponseValidation:
        """Devuelve si una respuesta respeta el conocimiento proporcionado."""


def validate_response(
    response: str,
    knowledge: str,
    semantic_validator: SemanticValidator | None = None,
) -> ResponseValidation:
    """Aplica límites críticos antes de publicar una respuesta."""
    reasons: list[str] = []
    normalized = response.strip() if isinstance(response, str) else ""
    if not normalized:
        reasons.append("La respuesta está vacía.")
    if len(normalized) > MAX_MESSAGE_LENGTH:
        reasons.append("La respuesta supera los 500 caracteres.")
    sentence_count = len(SENTENCE_ENDING_PATTERN.findall(normalized))
    if sentence_count > 3:
        reasons.append("La respuesta supera tres frases.")
    if INTERNAL_CONTENT_PATTERN.search(normalized):
        reasons.append("La respuesta contiene etiquetas o instrucciones internas.")

    result = ResponseValidation(valid=not reasons, reasons=tuple(reasons))
    if not result.valid or semantic_validator is None:
        return result
    return semantic_validator.validate(normalized, knowledge)

def limit_response_sentences(response: str, maximum: int = 3) -> str:
    """Conserva las primeras frases completas cuando solo sobra longitud verbal."""
    if maximum < 1 or not isinstance(response, str):
        return ""
    normalized = response.strip()
    sentences = re.findall(r"[^.!?]+(?:[.!?]+|$)", normalized)
    return "".join(sentences[:maximum]).strip()

def safe_response(should_close: bool) -> str:
    """Devuelve una alternativa natural que no afirma datos personales."""
    if should_close:
        return "De una, parce. Que te vaya muy bien y gracias por la charla 😊"
    return "Uy, de eso no te sabría decir, parce. ¿Qué más me contás?"
