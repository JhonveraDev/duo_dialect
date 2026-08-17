"""Ejecuta un claude_bot determinista en memoria o contra Google Sheets."""

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codex_bot.ai_provider import DeterministicAIProvider
from codex_bot.fake_sheet import FakeSheetClient
from codex_bot.constants import MESSAGE_LIMIT
from codex_bot.main import ConversationRunner
from codex_bot.responder import Responder
from codex_bot.sheet_client import GoogleSheetsClient
from codex_bot.simulator import ClaudeBotSimulator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("memory", "google"), default="memory")
    parser.add_argument("--interval", type=int, default=1)
    arguments = parser.parse_args()
    simulator = ClaudeBotSimulator()

    if arguments.mode == "memory":
        sheet = FakeSheetClient()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            knowledge = root / "knowledge.txt"
            knowledge.write_text("##HOBBIES\n- Contenido de prueba", encoding="utf-8")
            runner = ConversationRunner(
                sheet,
                Responder(
                    DeterministicAIProvider(), knowledge, logging.getLogger("sim")
                ),
                root / "state.json",
                "codex_bot",
                logging.getLogger("sim"),
            )
            while len(sheet.read_rows()) < MESSAGE_LIMIT:
                simulator.run_once(sheet)
                runner.run_once()
        print(f"Simulación local lista: {len(sheet.read_rows())} filas.")
        return 0

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    credentials = os.environ.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
    if not sheet_id or not Path(credentials).is_file():
        print("GOOGLE_SHEET_ID y GOOGLE_CREDENTIALS_PATH válidos son obligatorios.")
        return 2
    sheet = GoogleSheetsClient.from_service_account(credentials, sheet_id)
    while len(sheet.read_rows()) < MESSAGE_LIMIT:
        simulator.run_once(sheet)
        time.sleep(arguments.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
