"""Generación validada de respuestas a partir del conocimiento local."""

import logging
from pathlib import Path

from codex_bot.ai_provider import AIProvider
from codex_bot.knowledge import load_knowledge
from codex_bot.validator import SemanticValidator, safe_response, validate_response


class Responder:
    """Coordina proveedor, conocimiento y controles anti-alucinación."""

    def __init__(
        self,
        provider: AIProvider,
        knowledge_path: Path,
        logger: logging.Logger,
        semantic_validator: SemanticValidator | None = None,
    ) -> None:
        self._provider = provider
        self._knowledge_path = knowledge_path
        self._logger = logger
        self._semantic_validator = semantic_validator

    def generate(self, received_message: str, should_close: bool) -> str:
        """Genera, valida y sustituye por una respuesta segura cuando procede."""
        knowledge = load_knowledge(self._knowledge_path)
        response = self._provider.generate_response(
            received_message, knowledge, should_close
        )
        validation = validate_response(response, knowledge, self._semantic_validator)
        if validation.valid:
            return response.strip()
        self._logger.warning(
            "Respuesta reemplazada por validación: %s", validation.reasons
        )
        return safe_response(should_close)
