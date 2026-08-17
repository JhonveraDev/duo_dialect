"""Servidor local de solo lectura para visualizar el chat compartido."""

import json
import os
from collections.abc import Mapping, Sequence
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from codex_bot.models import ChatRow
from codex_bot.sheet_client import GoogleSheetsClient, SheetClientError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIRECTORY = PROJECT_ROOT / "web_demo"
DEFAULT_PORT = 8080


class WebConfigError(ValueError):
    """La configuración del visor local es incompleta o inválida."""


def messages_payload(rows: Sequence[ChatRow]) -> dict[str, list[dict[str, object]]]:
    """Convierte filas del dominio a un payload seguro para el navegador."""
    return {
        "messages": [
            {
                "id": row.id,
                "bot": row.bot,
                "mensaje": row.mensaje,
                "timestamp": row.timestamp,
            }
            for row in rows
        ]
    }


class ChatRequestHandler(SimpleHTTPRequestHandler):
    """Sirve la interfaz estática y el historial, sin exponer credenciales."""

    def __init__(self, *args: Any, sheet_client: GoogleSheetsClient, **kwargs: Any) -> None:
        self._sheet_client = sheet_client
        super().__init__(*args, directory=str(WEB_DIRECTORY), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/messages":
            self._send_messages()
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        self._send_json({"error": "El visor es de solo lectura."}, HTTPStatus.METHOD_NOT_ALLOWED)

    def _send_messages(self) -> None:
        try:
            payload = messages_payload(self._sheet_client.read_rows())
        except SheetClientError:
            self._send_json(
                {"error": "No fue posible leer el historial compartido."},
                HTTPStatus.BAD_GATEWAY,
            )
            return
        self._send_json(payload, HTTPStatus.OK)

    def _send_json(self, payload: object, status: HTTPStatus) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def load_sheet_client(environment: Mapping[str, str] | None = None) -> GoogleSheetsClient:
    """Crea un cliente de solo lectura a partir de variables de entorno."""
    values = os.environ if environment is None else environment
    sheet_id = values.get("GOOGLE_SHEET_ID", "").strip()
    credentials_path = Path(values.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json"))
    if not sheet_id:
        raise WebConfigError("GOOGLE_SHEET_ID es obligatorio para el visor.")
    if not credentials_path.is_file():
        raise WebConfigError("GOOGLE_CREDENTIALS_PATH debe apuntar a un archivo existente.")
    return GoogleSheetsClient.from_service_account(str(credentials_path), sheet_id)


def port_from_environment(environment: Mapping[str, str] | None = None) -> int:
    """Lee un puerto local válido sin mezclarlo con la configuración del bot."""
    values = os.environ if environment is None else environment
    raw_port = values.get("CHAT_UI_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError as error:
        raise WebConfigError("CHAT_UI_PORT debe ser un entero entre 1 y 65535.") from error
    if not 1 <= port <= 65535:
        raise WebConfigError("CHAT_UI_PORT debe estar entre 1 y 65535.")
    return port


def run_server(sheet_client: GoogleSheetsClient, port: int) -> None:
    """Inicia el visor en localhost hasta que el usuario pulse Ctrl+C."""
    handler = partial(ChatRequestHandler, sheet_client=sheet_client)
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Visor disponible en http://127.0.0.1:{port}")
        print("Pulsa Ctrl+C para detenerlo.")
        server.serve_forever()


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def main() -> int:
    """Carga la configuración e inicia el visor local."""
    _load_dotenv_if_available()
    try:
        run_server(load_sheet_client(), port_from_environment())
    except WebConfigError as error:
        print(f"Error de configuración del visor: {error}")
        return 2
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())