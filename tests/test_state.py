import tempfile
import unittest
from pathlib import Path

from codex_bot.models import LocalState
from codex_bot.state import load_state, save_state


class StateTests(unittest.TestCase):
    def test_ausencia_de_archivo_inicia_en_cero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_state(Path(directory) / "state.json"), LocalState())

    def test_guarda_y_recupera_estado(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_state(path, LocalState(ultimo_id_procesado=8))

            self.assertEqual(load_state(path), LocalState(ultimo_id_procesado=8))

    def test_estado_corrupto_se_recupera_en_cero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{no es json", encoding="utf-8")

            self.assertEqual(load_state(path), LocalState())
