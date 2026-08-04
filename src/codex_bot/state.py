"""Persistencia atómica del último mensaje procesado."""

import json
import tempfile
from pathlib import Path

from codex_bot.models import LocalState


def load_state(path: Path) -> LocalState:
    """Carga el estado o se recupera con el valor inicial ante datos corruptos."""
    if not path.exists():
        return LocalState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        last_processed_id = payload["ultimo_id_procesado"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return LocalState()
    if isinstance(last_processed_id, bool) or not isinstance(last_processed_id, int):
        return LocalState()
    if last_processed_id < 0:
        return LocalState()
    return LocalState(ultimo_id_procesado=last_processed_id)


def save_state(path: Path, state: LocalState) -> None:
    """Guarda el estado mediante reemplazo atómico en el mismo directorio."""
    if state.ultimo_id_procesado < 0:
        raise ValueError("ultimo_id_procesado no puede ser negativo.")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        {"ultimo_id_procesado": state.ultimo_id_procesado}, ensure_ascii=False
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(serialized)
            temporary_file.flush()
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
