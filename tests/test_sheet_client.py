import unittest

from codex_bot.models import ChatRow
from codex_bot.sheet_client import (
    GoogleSheetsClient,
    SheetContractError,
    TransientGoogleSheetsError,
    run_with_backoff,
)


class FakeHttpError(Exception):
    def __init__(self, status: int) -> None:
        self.resp = type("Response", (), {"status": status})()


class FakeRequest:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def execute(self) -> dict[str, object]:
        return self.payload


class FakeValuesApi:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.append_arguments: dict[str, object] | None = None

    def get(self, **kwargs: object) -> FakeRequest:
        del kwargs
        return FakeRequest(self.payload)

    def append(self, **kwargs: object) -> FakeRequest:
        self.append_arguments = kwargs
        return FakeRequest({})


class FakeSpreadsheetsApi:
    def __init__(self, values_api: FakeValuesApi) -> None:
        self.values_api = values_api

    def values(self) -> FakeValuesApi:
        return self.values_api


class FakeService:
    def __init__(self, payload: dict[str, object]) -> None:
        self.values_api = FakeValuesApi(payload)

    def spreadsheets(self) -> FakeSpreadsheetsApi:
        return FakeSpreadsheetsApi(self.values_api)


class SheetClientTests(unittest.TestCase):
    def test_lee_filas_con_cabecera_valida(self) -> None:
        service = FakeService(
            {
                "values": [
                    ["id", "bot", "mensaje", "timestamp"],
                    ["1", "claude_bot", "Hola", "2026-08-03T12:00:00Z"],
                ]
            }
        )
        client = GoogleSheetsClient(service, "sheet-id")

        self.assertEqual(client.read_rows()[0].id, 1)

    def test_rechaza_cabecera_incorrecta(self) -> None:
        client = GoogleSheetsClient(
            FakeService({"values": [["incorrecta"]]}), "sheet-id"
        )

        with self.assertRaises(SheetContractError):
            client.read_rows()

    def test_append_usa_los_parametros_contractuales(self) -> None:
        service = FakeService({"values": [["id", "bot", "mensaje", "timestamp"]]})
        client = GoogleSheetsClient(service, "sheet-id")
        row = ChatRow(2, "codex_bot", "Todo bien", "2026-08-03T12:00:00Z")

        client.append_row(row)

        arguments = service.values_api.append_arguments
        self.assertIsNotNone(arguments)
        assert arguments is not None
        self.assertEqual(arguments["valueInputOption"], "RAW")
        self.assertEqual(arguments["insertDataOption"], "INSERT_ROWS")
        self.assertEqual(arguments["range"], "chat!A:D")

    def test_reintenta_errores_transitorios(self) -> None:
        attempts = 0
        sleeps: list[float] = []

        def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise FakeHttpError(503)
            return "ok"

        self.assertEqual(run_with_backoff(operation, sleep=sleeps.append), "ok")
        self.assertEqual(sleeps, [1, 2])

    def test_agota_cinco_intentos_transitorios(self) -> None:
        def operation() -> object:
            raise FakeHttpError(429)

        with self.assertRaises(TransientGoogleSheetsError):
            run_with_backoff(operation, sleep=lambda _: None)
