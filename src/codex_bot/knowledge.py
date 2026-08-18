"""Acceso a la base de conocimiento local del bot."""

import re
import unicodedata
from pathlib import Path


class KnowledgeError(ValueError):
    """La base de conocimiento no está disponible para generar respuestas."""


def load_knowledge(path: Path) -> str:
    """Carga íntegramente una base pequeña UTF-8 y rechaza contenido vacío."""
    if not path.is_file():
        raise KnowledgeError(f"No existe la base de conocimiento: {path}.")
    try:
        knowledge = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise KnowledgeError(
            f"No se pudo leer la base de conocimiento: {path}."
        ) from error
    if not knowledge:
        raise KnowledgeError("La base de conocimiento está vacía.")
    return knowledge

STOP_WORDS = frozenset(
    {
        "como", "cuando", "donde", "quien", "quienes", "para", "porque",
        "sobre", "tengo", "tienes", "usted", "ustedes", "quiero", "podés",
        "puedes", "cuál", "cual", "qué", "que", "con", "por", "del", "las",
        "los", "una", "uno", "unos", "unas", "esta", "este", "eso", "más",
    }
)


def knowledge_backed_response(question: str, knowledge: str, should_close: bool) -> str:
    """Crea una alternativa breve usando literalmente un dato del archivo local."""
    if should_close:
        return "Vemos perrito, todo bien. Gracias por la charla."
    terms = {
        word.casefold()
        for word in re.findall(r"[\wáéíóúüñ]+", question)
        if len(word) >= 3 and word.casefold() not in STOP_WORDS
    }
    candidates = [line.strip()[1:].strip() for line in knowledge.splitlines() if line.strip().startswith("-")]
    selected = max(candidates, key=lambda line: _match_score(line, terms), default="")
    if not selected or not terms or _match_score(selected, terms) == 0:
        selected = candidates[0] if candidates else "No tengo información disponible."
    value = _fact_value(selected)
    response = value[:500].strip()
    return response if response else "No tengo información disponible."

def _match_score(line: str, terms: set[str]) -> int:
    normalized_line = _normalize_text(line)
    score = 0
    for term in terms:
        normalized_term = _normalize_text(term)
        if normalized_term in normalized_line:
            score += 2
        elif len(normalized_term) >= 4 and normalized_term[:4] in normalized_line:
            score += 1
    return score


def _normalize_text(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(character) != "Mn"
    )

def _fact_value(line: str) -> str:
    """Extrae el valor humano de una línea `- tema: valor` sin reformularlo."""
    value = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
    return value.strip(' "')