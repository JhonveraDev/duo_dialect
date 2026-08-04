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
