"""Lenguaje de primer orden configurable (Req. 1).

Los símbolos no lógicos son funciones (aridad >= 0; aridad 0 = constante) y
predicados (aridad >= 1). Todo identificador no declarado se trata como variable.
"""
import re

from .errores import Categoria, ErrorValidacion, Problema

IDENTIFICADOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*'*")
PALABRAS_RESERVADAS = {"forall", "exists"}


def es_identificador(nombre: str) -> bool:
    return IDENTIFICADOR.fullmatch(nombre) is not None and nombre not in PALABRAS_RESERVADAS


class Lenguaje:
    def __init__(self, funciones: dict[str, int] | None = None, predicados: dict[str, int] | None = None):
        funciones = dict(funciones or {})
        predicados = dict(predicados or {})
        problemas: list[Problema] = []

        for tipo, simbolos, minima in (("función", funciones, 0), ("predicado", predicados, 1)):
            for nombre, aridad in simbolos.items():
                if not es_identificador(nombre):
                    problemas.append(Problema(Categoria.LENGUAJE,
                                              f"'{nombre}' no es un nombre válido para un símbolo de {tipo}"))
                if not isinstance(aridad, int) or isinstance(aridad, bool) or aridad < minima:
                    problemas.append(Problema(Categoria.ARIDAD,
                                              f"La aridad de {tipo} '{nombre}' debe ser un entero >= {minima}"))

        for nombre in funciones.keys() & predicados.keys():
            problemas.append(Problema(Categoria.LENGUAJE,
                                      f"'{nombre}' está declarado como función y como predicado"))

        if problemas:
            raise ErrorValidacion(problemas)
        self.funciones = funciones
        self.predicados = predicados

    def es_funcion(self, nombre: str) -> bool:
        return nombre in self.funciones

    def es_predicado(self, nombre: str) -> bool:
        return nombre in self.predicados

    def es_simbolo(self, nombre: str) -> bool:
        return self.es_funcion(nombre) or self.es_predicado(nombre)

    def constantes(self) -> list[str]:
        return [f for f, n in self.funciones.items() if n == 0]
