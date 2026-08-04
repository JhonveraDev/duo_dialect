"""Infraestructura de Google Sheets que preserva el contrato compartido."""

import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any, Protocol, TypeVar

from codex_bot.constants import SHEET_HEADER, SHEET_NAME
from codex_bot.models import ChatRow

GOOGLE_SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
RETRY_DELAYS_SECONDS = (1, 2, 4, 8, 16)
MAX_OPERATION_ATTEMPTS = 5
T = TypeVar("T")


class SheetClient(Protocol):
    """Interfaz compartida por el cliente real y el doble en memoria."""

    def read_rows(self) -> list[ChatRow]:
        """Lee todas las filas de datos y valida la estructura de la hoja."""

    def append_row(self, row: ChatRow) -> None:
        """Añade una única fila mediante la operación permitida."""


class SheetClientError(RuntimeError):
    """Fallo de acceso o contrato del historial compartido."""


class SheetContractError(SheetClientError):
    """La pestaña o sus valores no respetan el contrato acordado."""


class TransientGoogleSheetsError(SheetClientError):
    """Fallo temporal agotado después de aplicar reintentos."""


def now_utc() -> str:
    """Obtiene una marca UTC con el formato contractual."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_with_backoff(
    operation: Callable[[], T],
    *,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Callable[[int, float], None] | None = None,
) -> T:
    """Reintenta 429/500/503 sin ocultar errores permanentes."""
    last_error: Exception | None = None
    for attempt in range(MAX_OPERATION_ATTEMPTS):
        try:
            return operation()
        except Exception as error:
            if not _is_transient_google_error(error):
                raise SheetClientError(
                    "Error no recuperable de Google Sheets."
                ) from error
            last_error = error
            if attempt < MAX_OPERATION_ATTEMPTS - 1:
                delay = RETRY_DELAYS_SECONDS[attempt]
                if on_retry is not None:
                    on_retry(attempt + 1, delay)
                sleep(delay)
    raise TransientGoogleSheetsError(
        f"Google Sheets falló tras {MAX_OPERATION_ATTEMPTS} intentos."
    ) from last_error


class GoogleSheetsClient:
    """Cliente mínimo que solo lee y agrega filas al rango chat!A:D."""

    def __init__(
        self,
        service: Any,
        spreadsheet_id: str,
        on_retry: Callable[[int, float], None] | None = None,
    ) -> None:
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._on_retry = on_retry

    @classmethod
    def from_service_account(
        cls,
        credentials_path: str,
        spreadsheet_id: str,
        on_retry: Callable[[int, float], None] | None = None,
    ) -> "GoogleSheetsClient":
        """Construye el cliente oficial usando una cuenta de servicio."""
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build  # type: ignore[import-untyped]
        except ImportError as error:
            raise RuntimeError(
                "Faltan dependencias Google; instala requirements.txt."
            ) from error
        credentials = Credentials.from_service_account_file(
            credentials_path, scopes=GOOGLE_SCOPES
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return cls(service, spreadsheet_id, on_retry)

    def read_rows(self) -> list[ChatRow]:
        """Lee cabecera y datos completos de la pestaña contractual."""
        payload = run_with_backoff(
            lambda: (
                self._service.spreadsheets()
                .values()
                .get(spreadsheetId=self._spreadsheet_id, range=f"{SHEET_NAME}!A:D")
                .execute()
            ),
            on_retry=self._on_retry,
        )
        values = payload.get("values", [])
        if not values:
            raise SheetContractError(
                "La pestaña chat no contiene la cabecera obligatoria."
            )
        if tuple(values[0]) != SHEET_HEADER:
            raise SheetContractError(
                "La cabecera debe ser exactamente: id | bot | mensaje | timestamp."
            )
        return [
            _row_from_values(row, position)
            for position, row in enumerate(values[1:], 2)
        ]

    def append_row(self, row: ChatRow) -> None:
        """Usa exclusivamente spreadsheets.values.append con RAW e INSERT_ROWS."""
        run_with_backoff(
            lambda: (
                self._service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"{SHEET_NAME}!A:D",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [[row.id, row.bot, row.mensaje, row.timestamp]]},
                )
                .execute()
            ),
            on_retry=self._on_retry,
        )


def _row_from_values(values: Sequence[object], position: int) -> ChatRow:
    if len(values) != 4:
        raise SheetContractError(
            f"La fila {position} debe tener exactamente cuatro columnas."
        )
    try:
        row_id = int(str(values[0]))
    except (TypeError, ValueError) as error:
        raise SheetContractError(
            f"El id de la fila {position} no es un entero."
        ) from error
    if (
        isinstance(values[1], str)
        and isinstance(values[2], str)
        and isinstance(values[3], str)
    ):
        return ChatRow(row_id, values[1], values[2], values[3])
    raise SheetContractError(f"La fila {position} tiene valores no textuales.")


def _is_transient_google_error(error: Exception) -> bool:
    response = getattr(error, "resp", None)
    status = getattr(response, "status", None)
    if status is None:
        status = getattr(error, "status_code", None)
    return status in {429, 500, 503}
