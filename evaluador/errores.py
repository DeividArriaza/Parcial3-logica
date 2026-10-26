"""Errores de validación del evaluador semántico.

Toda entrada incorrecta se reporta con una categoría (Req. 7) y nunca recibe
un valor de verdad.
"""
from dataclasses import dataclass
from enum import Enum


class Categoria(str, Enum):
    SINTAXIS = "sintaxis"
    SIMBOLO = "símbolo"
    ARIDAD = "aridad"
    LENGUAJE = "lenguaje"
    DOMINIO = "dominio"
    TUPLA = "tupla"
    ASIGNACION = "asignación"


@dataclass(frozen=True)
class Problema:
    categoria: Categoria
    mensaje: str
    posicion: int | None = None  # índice (0-based) dentro del texto de la fórmula

    def __str__(self) -> str:
        donde = f" (columna {self.posicion + 1})" if self.posicion is not None else ""
        return f"[{self.categoria.value}] {self.mensaje}{donde}"


class ErrorValidacion(Exception):
    """Agrupa uno o más problemas detectados en la entrada."""

    def __init__(self, problemas: list[Problema]):
        self.problemas = list(problemas)
        super().__init__("\n".join(str(p) for p in self.problemas))

    @classmethod
    def uno(cls, categoria: Categoria, mensaje: str, posicion: int | None = None) -> "ErrorValidacion":
        return cls([Problema(categoria, mensaje, posicion)])
