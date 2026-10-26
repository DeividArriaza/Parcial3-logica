"""Interpretación finita I = (D, fᴵ, Pᴵ) y entornos (Req. 2 y 4).

- D: dominio finito no vacío.
- fᴵ: D^n → D total (cada tupla de D^n tiene imagen en D).
- Pᴵ ⊆ D^n no vacía.
"""
from itertools import product

from .errores import Categoria, ErrorValidacion, Problema
from .lenguaje import Lenguaje

MAX_FALTANTES_MOSTRADAS = 5


def _tupla(t) -> str:
    return "(" + ", ".join(t) + ")"


class Interpretacion:
    def __init__(self, lenguaje: Lenguaje, dominio: list[str],
                 funciones: dict[str, dict[tuple, str]], relaciones: dict[str, set[tuple]]):
        self.lenguaje = lenguaje
        problemas: list[Problema] = []
        problemas += self._validar_dominio(dominio)
        if problemas:  # sin dominio válido no tiene sentido revisar tablas
            raise ErrorValidacion(problemas)
        self.dominio = list(dominio)
        conjunto = set(dominio)

        for nombre in funciones.keys() - lenguaje.funciones.keys():
            problemas.append(Problema(Categoria.SIMBOLO, f"'{nombre}' no es una función del lenguaje"))
        for nombre in relaciones.keys() - lenguaje.predicados.keys():
            problemas.append(Problema(Categoria.SIMBOLO, f"'{nombre}' no es un predicado del lenguaje"))

        for nombre, aridad in lenguaje.funciones.items():
            problemas += self._validar_funcion(nombre, aridad, funciones.get(nombre), conjunto)
        for nombre, aridad in lenguaje.predicados.items():
            problemas += self._validar_relacion(nombre, aridad, relaciones.get(nombre), conjunto)

        if problemas:
            raise ErrorValidacion(problemas)
        self.funciones = {f: dict(t) for f, t in funciones.items()}
        self.relaciones = {p: set(r) for p, r in relaciones.items()}

    @staticmethod
    def _validar_dominio(dominio: list[str]) -> list[Problema]:
        if not dominio:
            return [Problema(Categoria.DOMINIO, "El dominio D no puede ser vacío")]
        problemas = []
        for e in dominio:
            if not isinstance(e, str) or not e.strip() or any(c in e for c in "(),"):
                problemas.append(Problema(Categoria.DOMINIO, f"'{e}' no es un nombre válido de elemento"))
        repetidos = sorted({e for e in dominio if dominio.count(e) > 1})
        if repetidos:
            problemas.append(Problema(Categoria.DOMINIO, f"Elementos repetidos en D: {', '.join(repetidos)}"))
        return problemas

    @staticmethod
    def _validar_funcion(nombre, aridad, tabla, dominio: set) -> list[Problema]:
        etiqueta = f"constante '{nombre}'" if aridad == 0 else f"función '{nombre}'"
        if not tabla:
            return [Problema(Categoria.TUPLA, f"Falta la interpretación de la {etiqueta}")]
        problemas = []
        for args, valor in tabla.items():
            if len(args) != aridad:
                problemas.append(Problema(Categoria.ARIDAD,
                                          f"{etiqueta}: la tupla {_tupla(args)} no tiene {aridad} componente(s)"))
            elif not set(args) <= dominio:
                problemas.append(Problema(Categoria.TUPLA,
                                          f"{etiqueta}: la tupla {_tupla(args)} tiene elementos fuera de D"))
            if valor not in dominio:
                problemas.append(Problema(Categoria.DOMINIO,
                                          f"{etiqueta}: la imagen '{valor}' de {_tupla(args)} no pertenece a D"))
        faltantes = [t for t in product(sorted(dominio), repeat=aridad) if t not in tabla]
        if faltantes:
            muestra = ", ".join(_tupla(t) for t in faltantes[:MAX_FALTANTES_MOSTRADAS])
            extra = f" y {len(faltantes) - MAX_FALTANTES_MOSTRADAS} más" if len(faltantes) > MAX_FALTANTES_MOSTRADAS else ""
            problemas.append(Problema(Categoria.TUPLA,
                                      f"{etiqueta} no es total: falta la imagen de {muestra}{extra}"))
        return problemas

    @staticmethod
    def _validar_relacion(nombre, aridad, relacion, dominio: set) -> list[Problema]:
        if not relacion:
            return [Problema(Categoria.TUPLA, f"La relación del predicado '{nombre}' no puede ser vacía")]
        problemas = []
        for t in relacion:
            if len(t) != aridad:
                problemas.append(Problema(Categoria.ARIDAD,
                                          f"Predicado '{nombre}': la tupla {_tupla(t)} no tiene {aridad} componente(s)"))
            elif not set(t) <= dominio:
                problemas.append(Problema(Categoria.TUPLA,
                                          f"Predicado '{nombre}': la tupla {_tupla(t)} tiene elementos fuera de D"))
        return problemas

    def validar_entorno(self, libres: list[str], entorno: dict[str, str]) -> dict[str, str]:
        """Devuelve σ restringido a las variables libres o lanza ErrorValidacion."""
        problemas = []
        for x in libres:
            if x not in entorno or entorno[x] in (None, ""):
                problemas.append(Problema(Categoria.ASIGNACION, f"Falta asignar un valor de D a la variable libre '{x}'"))
            elif entorno[x] not in self.dominio:
                problemas.append(Problema(Categoria.ASIGNACION,
                                          f"σ({x}) = '{entorno[x]}' no pertenece al dominio D"))
        if problemas:
            raise ErrorValidacion(problemas)
        return {x: entorno[x] for x in libres}
