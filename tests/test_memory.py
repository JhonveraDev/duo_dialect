import unittest

from codex_bot.memory import (
    MemoryContractError,
    MemoryManager,
    active_records,
    memory_context,
    validate_memory_record,
)
from codex_bot.models import ChatRow, MemoryRecord


def record(**changes: str) -> MemoryRecord:
    values = {
        "id": "r_12345678",
        "sujeto": "amigo",
        "texto": "Está pensando en comprarse un carro",
        "tipo": "plan",
        "estado": "sin_confirmar",
        "fecha": "2026-08-11",
        "origen": "conv_oficial_001#msg_8",
        "reemplaza_a": "",
        "entorno": "oficial",
    }
    values.update(changes)
    return MemoryRecord(**values)

class InMemoryMemoryClient:
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []
        self.archived_rows: list[ChatRow] = []

    def read_records(self) -> list[MemoryRecord]:
        return list(self.records)

    def archive_conversation(self, rows: list[ChatRow]) -> str:
        self.archived_rows = list(rows)
        return "conv_oficial_001_2026-08-17"

    def append_record(self, item: MemoryRecord) -> None:
        self.records.append(item)


class EmptyExtractor:
    def extract_memories(
        self, rows: list[ChatRow], knowledge: str, existing: list[MemoryRecord]
    ) -> list[object]:
        del rows, knowledge, existing
        return []


def conversation() -> list[ChatRow]:
    return [
        ChatRow(
            index,
            "claude_bot" if index % 2 else "codex_bot",
            f"Mensaje {index}",
            "2026-08-17T20:00:00Z",
        )
        for index in range(1, 25)
    ]

class MemoryTests(unittest.TestCase):
    def test_valida_un_recuerdo_con_procedencia(self) -> None:
        validate_memory_record(record())

    def test_rechaza_tipo_desconocido(self) -> None:
        with self.assertRaisesRegex(MemoryContractError, "Tipo"):
            validate_memory_record(record(tipo="otro"))

    def test_ignora_recuerdos_descartados_reemplazados_y_de_pruebas(self) -> None:
        records = [
            record(),
            record(id="r_23456789", estado="descartado"),
            record(id="r_34567890", estado="reemplazado"),
            record(id="r_45678901", entorno="pruebas"),
        ]

        self.assertEqual(active_records(records), [records[0]])

    def test_el_contexto_separa_planes_abiertos(self) -> None:
        context = memory_context(
            [record(), record(id="r_23456789", texto="Trabaja remoto", tipo="hecho")]
        )

        self.assertIn("TEMAS ABIERTOS", context)
        self.assertIn("Está pensando", context)
        self.assertIn("RECUERDOS DEL AMIGO", context)
        self.assertIn("Trabaja remoto", context)

    def test_guarda_y_recupera_intercambios_de_conversaciones_anteriores(self) -> None:
        client = InMemoryMemoryClient()
        manager = MemoryManager(client, EmptyExtractor())  # type: ignore[arg-type]

        stored = manager.remember(conversation(), "dato")
        context = manager.context()

        self.assertEqual(stored, 12)
        self.assertEqual(len(client.archived_rows), 24)
        self.assertIn("INTERCAMBIOS ANTERIORES", context)
        self.assertIn("Pregunta previa: Mensaje 1", context)
        self.assertIn("Respuesta previa: Mensaje 2", context)
        self.assertTrue(all(item.sujeto == "conversacion" for item in client.records))
    def test_el_contexto_vacio_no_agrega_informacion(self) -> None:
        self.assertEqual(memory_context([record(estado="descartado")]), "")