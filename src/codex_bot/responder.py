"""Generación validada de respuestas a partir del conocimiento local."""

import logging
from pathlib import Path

from codex_bot.ai_provider import AIProvider
from codex_bot.knowledge import load_knowledge
from codex_bot.memory import MemoryManager
from codex_bot.models import ChatRow
from codex_bot.web_lookup import DisabledWebLookupProvider, WebLookupProvider
from codex_bot.validator import SemanticValidator, safe_response, validate_response


class Responder:
    """Coordina proveedor, conocimiento y controles anti-alucinación."""

    def __init__(
        self,
        provider: AIProvider,
        knowledge_path: Path,
        logger: logging.Logger,
        semantic_validator: SemanticValidator | None = None,
        memory_manager: MemoryManager | None = None,
        web_lookup: WebLookupProvider | None = None,
    ) -> None:
        self._provider = provider
        self._knowledge_path = knowledge_path
        self._logger = logger
        self._semantic_validator = semantic_validator
        self._memory_manager = memory_manager
        self._web_lookup = web_lookup or DisabledWebLookupProvider()

    def generate(self, received_message: str, should_close: bool) -> str:
        """Genera, valida y sustituye por una respuesta segura cuando procede."""
        knowledge = load_knowledge(self._knowledge_path)
        memory_context = self._memory_manager.context() if self._memory_manager else ""
        web_context = self._web_lookup.lookup(received_message).as_prompt_context()
        contexts = [knowledge, memory_context, web_context]
        full_context = "\n\n".join(context for context in contexts if context)
        response = self._provider.generate_response(
            received_message, full_context, should_close
        )
        validation = validate_response(response, full_context, self._semantic_validator)
        if validation.valid:
            return response.strip()
        self._logger.warning(
            "Respuesta reemplazada por validación: %s", validation.reasons
        )
        return safe_response(should_close)
    def remember_conversation(self, rows: list[ChatRow]) -> int:
        """Extrae recuerdos privados al cerrar, sin modificar chat."""
        if self._memory_manager is None:
            return 0
        return self._memory_manager.remember(rows, load_knowledge(self._knowledge_path))
