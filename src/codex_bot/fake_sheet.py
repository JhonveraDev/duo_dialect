"""Doble en memoria del cliente Google Sheets para pruebas locales."""

from collections.abc import Sequence

from codex_bot.conversation import validar_historial
from codex_bot.models import ChatRow
from codex_bot.sheet_client import SheetContractError


class FakeSheetClient:
    """Historial en memoria con el mismo contrato público que el cliente real."""

    def __init__(self, rows: Sequence[ChatRow] = ()) -> None:
        self._rows = list(rows)

    def read_rows(self) -> list[ChatRow]:
        validar_historial(self._rows)
        return list(self._rows)

    def append_row(self, row: ChatRow) -> None:
        candidate = [*self._rows, row]
        try:
            validar_historial(candidate)
        except ValueError as error:
            raise SheetContractError(
                "El append incumple el contrato del historial."
            ) from error
        self._rows.append(row)
