"""Punto de entrada y bucle de polling de codex_bot."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from codex_bot.ai_provider import create_ai_provider
from codex_bot.config import ConfigError, Settings
from codex_bot.conversation import (
    conversacion_terminada,
    debo_cerrar,
    es_mi_turno,
    siguiente_id,
    validar_historial,
)
from codex_bot.logging_config import configure_logging
from codex_bot.models import ChatRow, LocalState
from codex_bot.responder import Responder
from codex_bot.sheet_client import (
    GoogleSheetsClient,
    SheetClient,
    TransientGoogleSheetsError,
    now_utc,
)
from codex_bot.state import load_state, save_state

WAIT_LOG_INTERVAL_SECONDS = 300


class CycleResult(Enum):
    """Resultado observable de una iteración del bucle."""

    APPENDED = "appended"
    WAITING = "waiting"
    CONCURRENT_CHANGE = "concurrent_change"
    FINISHED = "finished"


@dataclass(slots=True)
class ConversationRunner:
    """Orquesta un ciclo sin conocer detalles de Google ni del modelo de IA."""

    sheet_client: SheetClient
    responder: Responder
    state_path: Path
    bot_id: str
    logger: logging.Logger
    state: LocalState | None = None

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = load_state(self.state_path)

    def run_once(self) -> CycleResult:
        """Procesa como máximo un mensaje del otro bot según el contrato."""
        rows = self.sheet_client.read_rows()
        validar_historial(rows)
        self.logger.debug("Historial leído: %d filas.", len(rows))

        if conversacion_terminada(rows):
            self.logger.info("Conversación terminada con 16 filas.")
            return CycleResult.FINISHED

        state = self.state
        if state is None:
            raise RuntimeError("El estado local no se inicializó.")
        if not rows:
            if state.ultimo_id_procesado:
                self.state = LocalState(ultimo_id_procesado=0)
                save_state(self.state_path, self.state)
                self.logger.info("Estado local reiniciado: el historial está vacío.")
            return CycleResult.WAITING
        if not es_mi_turno(rows, self.bot_id):
            return CycleResult.WAITING

        received_row = rows[-1]
        if received_row.id <= state.ultimo_id_procesado:
            return CycleResult.WAITING

        should_close = debo_cerrar(rows, self.bot_id)
        self.logger.info("Mensaje detectado: id=%d.", received_row.id)
        response = self.responder.generate(received_row.mensaje, should_close)
        self.logger.info("Respuesta generada para id=%d.", received_row.id)

        refreshed_rows = self.sheet_client.read_rows()
        validar_historial(refreshed_rows)
        if refreshed_rows != rows:
            self.logger.info(
                "Respuesta descartada: el historial cambió durante la generación."
            )
            return CycleResult.CONCURRENT_CHANGE

        new_row = ChatRow(
            id=siguiente_id(rows),
            bot=self.bot_id,
            mensaje=response,
            timestamp=now_utc(),
        )
        self.sheet_client.append_row(new_row)
        self.state = LocalState(ultimo_id_procesado=received_row.id)
        save_state(self.state_path, self.state)
        self.logger.info("Append exitoso: id=%d.", new_row.id)
        return CycleResult.APPENDED


def run(settings: Settings) -> int:
    """Ejecuta polling hasta completar el contrato o recibir Ctrl+C."""
    logger = configure_logging(settings.log_level)
    logger.info("Arranque de codex_bot.")
    client = GoogleSheetsClient.from_service_account(
        str(settings.google_credentials_path),
        settings.google_sheet_id,
        on_retry=lambda attempt, delay: logger.warning(
            "Reintento Google Sheets %d en %.0f s.", attempt, delay
        ),
    )
    responder = Responder(create_ai_provider(settings), settings.knowledge_file, logger)
    runner = ConversationRunner(
        client, responder, settings.state_file, settings.bot_id, logger
    )
    return run_polling(runner, settings.poll_interval_seconds, logger)


def run_polling(
    runner: ConversationRunner,
    poll_interval_seconds: int,
    logger: logging.Logger,
    *,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    """Mantiene el polling y conserva vivos los fallos transitorios de Google."""
    last_wait_log = monotonic()
    try:
        while True:
            try:
                result = runner.run_once()
            except TransientGoogleSheetsError as error:
                logger.warning(
                    "Google Sheets sigue temporalmente no disponible: %s", error
                )
                sleep(poll_interval_seconds)
                continue
            if result is CycleResult.FINISHED:
                return 0
            if result is CycleResult.CONCURRENT_CHANGE:
                continue
            if monotonic() - last_wait_log >= WAIT_LOG_INTERVAL_SECONDS:
                logger.info("Esperando un mensaje de claude_bot.")
                last_wait_log = monotonic()
            sleep(poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Apagado limpio solicitado por el usuario.")
        return 0


def main() -> int:
    """Carga `.env`, valida la configuración y ejecuta el proceso real."""
    _configure_console_utf8()
    try:
        _load_dotenv_if_available()
        settings = Settings.from_environment(require_credentials=True)
        return run(settings)
    except ConfigError as error:
        print(f"Error de configuración: {error}")
        return 2
    except Exception as error:
        print(f"Error fatal de codex_bot: {error}")
        return 1


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _configure_console_utf8() -> None:
    """Evita que un emoji en un log rompa el proceso en consolas Windows."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    raise SystemExit(main())
