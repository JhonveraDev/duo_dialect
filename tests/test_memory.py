import unittest

from codex_bot.memory import MemoryContractError, active_records, memory_context, validate_memory_record
from codex_bot.models import MemoryRecord


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

    def test_el_contexto_vacio_no_agrega_informacion(self) -> None:
        self.assertEqual(memory_context([record(estado="descartado")]), "")