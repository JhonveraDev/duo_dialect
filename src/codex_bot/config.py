"""Carga y validación de configuración, sin exponer secretos."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from codex_bot.constants import BOT_ID, MESSAGE_LIMIT

MINIMUM_POLL_INTERVAL_SECONDS = 5
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class ConfigError(ValueError):
    """La configuración de ejecución no cumple los requisitos."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Valores configurables ya validados para el proceso."""

    google_sheet_id: str
    google_credentials_path: Path
    bot_id: str
    poll_interval_seconds: int
    message_limit: int
    ai_provider: str
    ai_api_key: str
    ai_model: str
    log_level: str
    state_file: Path
    knowledge_file: Path
    memory_sheet_id: str
    web_lookup_enabled: bool

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        require_credentials: bool = False,
    ) -> "Settings":
        """Crea ajustes desde un mapeo, normalmente las variables de entorno."""
        values = os.environ if environment is None else environment
        provider = _required(values, "AI_PROVIDER")
        api_key = values.get("AI_API_KEY", "").strip()
        model = values.get("AI_MODEL", "").strip()
        if provider != "fake" and (not api_key or not model):
            raise ConfigError(
                "AI_API_KEY y AI_MODEL son obligatorios para un proveedor real."
            )

        settings = cls(
            google_sheet_id=_required(values, "GOOGLE_SHEET_ID"),
            google_credentials_path=Path(
                values.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
            ),
            bot_id=_required(values, "BOT_ID"),
            poll_interval_seconds=_positive_integer(values, "INTERVALO_LECTURA"),
            message_limit=_positive_integer(values, "LIMITE_MENSAJES"),
            ai_provider=provider,
            ai_api_key=api_key,
            ai_model=model,
            log_level=values.get("LOG_LEVEL", "INFO").strip().upper(),
            state_file=Path(values.get("STATE_FILE", "./state.json")),
            knowledge_file=Path(
                values.get("KNOWLEDGE_FILE", "./data/mi_informacion.txt")
            ),
            memory_sheet_id=values.get("MEMORY_SHEET_ID", "").strip(),
            web_lookup_enabled=_boolean(values, "WEB_LOOKUP_ENABLED", default=False),
        )
        settings.validate(require_credentials=require_credentials)
        return settings

    def validate(self, *, require_credentials: bool) -> None:
        """Comprueba invariantes y archivos locales necesarios al arrancar."""
        if self.bot_id != BOT_ID:
            raise ConfigError(f"BOT_ID debe ser exactamente {BOT_ID!r}.")
        if self.message_limit != MESSAGE_LIMIT:
            raise ConfigError(f"LIMITE_MENSAJES debe ser exactamente {MESSAGE_LIMIT}.")
        if self.poll_interval_seconds < MINIMUM_POLL_INTERVAL_SECONDS:
            raise ConfigError(
                "INTERVALO_LECTURA debe ser >= "
                f"{MINIMUM_POLL_INTERVAL_SECONDS} segundos."
            )
        if self.log_level not in VALID_LOG_LEVELS:
            raise ConfigError("LOG_LEVEL no es un nivel de logging válido.")
        if (
            not self.knowledge_file.is_file()
            or not self.knowledge_file.read_text(encoding="utf-8").strip()
        ):
            raise ConfigError("KNOWLEDGE_FILE debe existir y no estar vacío.")
        if require_credentials and not self.google_credentials_path.is_file():
            raise ConfigError(
                "No se encontró GOOGLE_CREDENTIALS_PATH para la ejecución real."
            )


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ConfigError(f"La variable {name} es obligatoria.")
    return value


def _positive_integer(values: Mapping[str, str], name: str) -> int:
    raw_value = _required(values, name)
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigError(f"{name} debe ser un entero positivo.") from error
    if value <= 0:
        raise ConfigError(f"{name} debe ser un entero positivo.")
    return value


def _boolean(values: Mapping[str, str], name: str, *, default: bool) -> bool:
    raw_value = values.get(name, str(default)).strip().casefold()
    if raw_value in {"1", "true", "si", "sí", "yes"}:
        return True
    if raw_value in {"0", "false", "no"}:
        return False
    raise ConfigError(f"{name} debe ser true o false.")