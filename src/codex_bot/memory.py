"""Memoria privada de codex_bot, aislada del historial compartido."""

from collections.abc import Sequence
from datetime import date
import re
from uuid import uuid4
from typing import Any, Protocol

from codex_bot.models import ChatRow, MemoryProposal, MemoryRecord
from codex_bot.sheet_client import run_with_backoff

MEMORY_SHEET_NAME = "recuerdos"
ARCHIVE_HEADER = ("id", "bot", "mensaje", "timestamp")
ARCHIVE_TITLE_PATTERN = re.compile(r"^conv_oficial_(\d{3})_")
MEMORY_HEADER = (
    "id",
    "sujeto",
    "texto",
    "tipo",
    "estado",
    "fecha",
    "origen",
    "reemplaza_a",
    "entorno",
)
MEMORY_TYPES = frozenset({"hecho", "preferencia", "relacion", "evento", "plan"})
MEMORY_STATES = frozenset(
    {"sin_confirmar", "confirmado", "descartado", "reemplazado"}
)
ACTIVE_MEMORY_STATES = frozenset({"sin_confirmar", "confirmado"})


class MemoryClient(Protocol):
    """Contrato de almacenamiento privado de recuerdos."""

    def read_records(self) -> list[MemoryRecord]:
        """Lee todos los recuerdos conservando su trazabilidad."""

    def archive_conversation(self, rows: Sequence[ChatRow]) -> str:
        """Copia las 16 filas a una pestaña privada sin tocar chat."""
        if len(rows) != 16:
            raise MemoryContractError("Solo se puede archivar una conversación de 16 filas.")
        metadata = run_with_backoff(
            lambda: self._service.spreadsheets().get(
                spreadsheetId=self._spreadsheet_id, fields="sheets.properties"
            ).execute()
        )
        titles = [sheet["properties"]["title"] for sheet in metadata.get("sheets", [])]
        numbers = [int(match.group(1)) for title in titles if (match := ARCHIVE_TITLE_PATTERN.match(title))]
        title = f"conv_oficial_{max(numbers, default=0) + 1:03d}_{date.today().isoformat()}"
        run_with_backoff(
            lambda: self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
            ).execute()
        )
        values = [list(ARCHIVE_HEADER)] + [
            [row.id, row.bot, row.mensaje, row.timestamp] for row in rows
        ]
        run_with_backoff(
            lambda: self._service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id, range=f"'{title}'!A:D",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": values},
            ).execute()
        )
        return title
    def archive_conversation(self, rows: Sequence[ChatRow]) -> str:
        """Archiva una conversación cerrada en una pestaña privada."""

    def append_record(self, record: MemoryRecord) -> None:
        """Añade un recuerdo sin reescribir la hoja completa."""


class MemoryContractError(ValueError):
    """La hoja privada de recuerdos no cumple el formato esperado."""


def validate_memory_record(record: MemoryRecord) -> None:
    """Valida los nueve campos antes de persistir un recuerdo."""
    if not record.id.startswith("r_") or len(record.id) < 6:
        raise MemoryContractError("El id del recuerdo debe empezar por 'r_'.")
    if record.sujeto != "amigo":
        raise MemoryContractError("La memoria automática solo admite sujeto 'amigo'.")
    if not record.texto.strip():
        raise MemoryContractError("El texto del recuerdo no puede estar vacío.")
    if record.tipo not in MEMORY_TYPES:
        raise MemoryContractError(f"Tipo de recuerdo inválido: {record.tipo!r}.")
    if record.estado not in MEMORY_STATES:
        raise MemoryContractError(f"Estado de recuerdo inválido: {record.estado!r}.")
    try:
        date.fromisoformat(record.fecha)
    except ValueError as error:
        raise MemoryContractError("La fecha debe usar el formato YYYY-MM-DD.") from error
    if not record.origen.strip():
        raise MemoryContractError("El origen del recuerdo es obligatorio.")
    if record.entorno != "oficial":
        raise MemoryContractError("Solo se admiten recuerdos del entorno oficial.")


def active_records(records: Sequence[MemoryRecord]) -> list[MemoryRecord]:
    """Devuelve recuerdos vigentes, aislando los datos de pruebas y descartados."""
    return [
        record
        for record in records
        if record.estado in ACTIVE_MEMORY_STATES and record.entorno == "oficial"
    ]


def memory_context(records: Sequence[MemoryRecord]) -> str:
    """Construye el bloque que se añade al prompt para retomar temas abiertos."""
    active = active_records(records)
    if not active:
        return ""
    plans = [record for record in active if record.tipo == "plan"]
    others = [record for record in active if record.tipo != "plan"]
    sections: list[str] = []
    if plans:
        sections.append(
            "TEMAS ABIERTOS DEL AMIGO (puedes retomarlos con naturalidad):\n"
            + "\n".join(f"- {record.texto}" for record in plans)
        )
    if others:
        sections.append(
            "RECUERDOS DEL AMIGO (no los atribuyas a ti):\n"
            + "\n".join(f"- {record.texto}" for record in others)
        )
    return "\n\n".join(sections)



class MemoryExtractor(Protocol):
    """Extrae hechos sobre el interlocutor al cerrar una conversación."""

    def extract_memories(
        self, rows: Sequence[ChatRow], knowledge: str, existing: Sequence[MemoryRecord]
    ) -> list[MemoryProposal]:
        """Devuelve propuestas basadas exclusivamente en mensajes de claude_bot."""


class MemoryManager:
    """Orquesta contexto y persistencia, siempre en la hoja privada."""

    def __init__(self, client: MemoryClient, extractor: MemoryExtractor) -> None:
        self._client = client
        self._extractor = extractor

    def context(self) -> str:
        return memory_context(self._client.read_records())

    def remember(self, rows: Sequence[ChatRow], knowledge: str) -> int:
        if len(rows) != 16:
            return 0
        archive_name = self._client.archive_conversation(rows)
        existing = self._client.read_records()
        known_origins = {record.origen for record in existing}
        known_texts = {_normalize(record.texto) for record in existing}
        stored = 0
        for proposal in self._extractor.extract_memories(rows, knowledge, existing):
            origin = f"{archive_name}#msg_{proposal.msg}"
            text = proposal.texto.strip()
            if origin in known_origins or not text or _normalize(text) in known_texts:
                continue
            record = MemoryRecord(
                id=f"r_{uuid4().hex[:12]}", sujeto="amigo", texto=text,
                tipo=proposal.tipo if proposal.tipo in MEMORY_TYPES else "hecho",
                estado="sin_confirmar", fecha=date.today().isoformat(), origen=origin,
                reemplaza_a=proposal.reemplaza_a if any(
                    item.id == proposal.reemplaza_a for item in existing
                ) else "", entorno="oficial",
            )
            self._client.append_record(record)
            known_origins.add(origin)
            known_texts.add(_normalize(text))
            stored += 1
        return stored


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())

class GoogleSheetsMemoryClient:
    """Cliente mínimo para la hoja privada, nunca para el Sheet compartido."""

    def __init__(self, service: Any, spreadsheet_id: str) -> None:
        self._service = service
        self._spreadsheet_id = spreadsheet_id

    @classmethod
    def from_service_account(
        cls, credentials_path: str, spreadsheet_id: str
    ) -> "GoogleSheetsMemoryClient":
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build  # type: ignore[import-untyped]
        except ImportError as error:
            raise RuntimeError("Faltan dependencias Google; instala requirements.txt.") from error
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=("https://www.googleapis.com/auth/spreadsheets",),
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return cls(service, spreadsheet_id)

    def read_records(self) -> list[MemoryRecord]:
        payload = run_with_backoff(
            lambda: (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"{MEMORY_SHEET_NAME}!A:I",
                )
                .execute()
            )
        )
        values = payload.get("values", [])
        if not values or tuple(values[0]) != MEMORY_HEADER:
            raise MemoryContractError(
                "La pestaña recuerdos debe tener la cabecera de nueve columnas."
            )
        records = [
            _record_from_values(_complete_values(row), position)
            for position, row in enumerate(values[1:], 2)
        ]
        for record in records:
            validate_memory_record(record)
        return records

    def archive_conversation(self, rows: Sequence[ChatRow]) -> str:
        """Copia las 16 filas a una pestaña privada sin tocar chat."""
        if len(rows) != 16:
            raise MemoryContractError("Solo se puede archivar una conversación de 16 filas.")
        metadata = run_with_backoff(
            lambda: self._service.spreadsheets().get(
                spreadsheetId=self._spreadsheet_id, fields="sheets.properties"
            ).execute()
        )
        titles = [sheet["properties"]["title"] for sheet in metadata.get("sheets", [])]
        numbers = [int(match.group(1)) for title in titles if (match := ARCHIVE_TITLE_PATTERN.match(title))]
        title = f"conv_oficial_{max(numbers, default=0) + 1:03d}_{date.today().isoformat()}"
        run_with_backoff(
            lambda: self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
            ).execute()
        )
        values = [list(ARCHIVE_HEADER)] + [
            [row.id, row.bot, row.mensaje, row.timestamp] for row in rows
        ]
        run_with_backoff(
            lambda: self._service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id, range=f"'{title}'!A:D",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": values},
            ).execute()
        )
        return title
    def archive_conversation(self, rows: Sequence[ChatRow]) -> str:
        """Archiva una conversación cerrada en una pestaña privada."""

    def append_record(self, record: MemoryRecord) -> None:
        validate_memory_record(record)
        run_with_backoff(
            lambda: (
                self._service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"{MEMORY_SHEET_NAME}!A:I",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [[
                        record.id,
                        record.sujeto,
                        record.texto,
                        record.tipo,
                        record.estado,
                        record.fecha,
                        record.origen,
                        record.reemplaza_a,
                        record.entorno,
                    ]]},
                )
                .execute()
            )
        )


def _complete_values(values: Sequence[object]) -> tuple[object, ...]:
    if len(values) > len(MEMORY_HEADER):
        raise MemoryContractError("Una fila de recuerdos tiene más de nueve columnas.")
    return tuple(values) + ("",) * (len(MEMORY_HEADER) - len(values))


def _record_from_values(values: Sequence[object], position: int) -> MemoryRecord:
    if not all(isinstance(value, str) for value in values):
        raise MemoryContractError(f"La fila {position} contiene valores no textuales.")
    return MemoryRecord(*values)