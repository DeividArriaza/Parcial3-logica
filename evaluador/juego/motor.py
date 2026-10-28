"""Compatibilidad con la API histórica del motor, implementada en módulos específicos."""
from .tipos import (
    ALTO, ANCHO, CONFIG_TIPOS, COSTO_BASE, COSTO_CONECTIVO, COSTO_CUANTIFICADOR,
    ENERGIA_INICIAL, ENERGIA_MAXIMA, ENERGIA_POR_TURNO, LENGUAJE,
)
from .partida import crear_estado
from .niveles import niveles
from .reglas import atacar, mover, posiciones_alcanzables, previsualizar, terminar_turno
