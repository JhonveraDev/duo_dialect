"""Modelos inmutables del dominio."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatRow:
    """Una fila de datos del historial compartido."""

    id: int
    bot: str
    mensaje: str
    timestamp: str


@dataclass(frozen=True, slots=True)
class LocalState:
    """Estado local persistente usado para evitar respuestas duplicadas."""

    ultimo_id_procesado: int = 0

@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """Hecho persistente sobre el interlocutor, con trazabilidad completa."""

    id: str
    sujeto: str
    texto: str
    tipo: str
    estado: str
    fecha: str
    origen: str
    reemplaza_a: str = ""
    entorno: str = "oficial"

@dataclass(frozen=True, slots=True)
class MemoryProposal:
    """Propuesta de recuerdo extraída de una conversación cerrada."""

    msg: int
    texto: str
    tipo: str = "hecho"
    reemplaza_a: str = ""
