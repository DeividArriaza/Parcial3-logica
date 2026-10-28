"""Tipos de unidad, lenguaje y constantes de balance."""
from evaluador.lenguaje import Lenguaje
ANCHO, ALTO = 10, 8
CONFIG_TIPOS = {
    "Infante": {"vida": 10, "mov": 3, "alcance": 1, "poder": 4},
    "Arquero": {"vida": 7, "mov": 2, "alcance": 4, "poder": 3},
    "Medico": {"vida": 7, "mov": 3, "alcance": 2, "poder": 3},
    "Tanque": {"vida": 16, "mov": 1, "alcance": 2, "poder": 5},
}
COSTO_BASE, COSTO_CONECTIVO, COSTO_CUANTIFICADOR = 1, 1, 2
ENERGIA_INICIAL, ENERGIA_POR_TURNO, ENERGIA_MAXIMA = 10, 6, 15
LENGUAJE = Lenguaje(funciones={"yo": 0}, predicados={"Mio": 1, "Enemigo": 1, "Herido": 1, "Infante": 1,
                                "Arquero": 1, "Medico": 1, "Tanque": 1, "EnAgua": 1,
                                "Cerca": 2, "Alineado": 2})



