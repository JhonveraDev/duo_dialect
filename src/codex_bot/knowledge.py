"""Acceso a la base de conocimiento local del bot."""

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
