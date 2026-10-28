"""Interpretación del tablero y consultas de unidades vivas."""
from .tipos import ALTO, ANCHO, LENGUAJE
from .validacion import _problema


class InterpretacionJuego:
    """Estructura compatible con Evaluador que admite relaciones vacías."""

    def __init__(self, dominio, relaciones, yo=""):
        """Conserva el dominio vivo y la constante relativa al atacante."""
        self.dominio = list(dominio)
        self.funciones = {"yo": {(): yo}}
        self.relaciones = relaciones


def _mapa() -> dict:
    """Construye el terreno del juego libre."""
    terreno = [["pasto" for _ in range(ANCHO)] for _ in range(ALTO)]
    for col, fila in ((4, 1), (5, 1), (4, 6), (5, 6), (2, 3), (7, 4)):
        terreno[fila][col] = "agua"
    for col, fila in ((4, 3), (5, 3), (4, 4), (5, 4)):
        terreno[fila][col] = "muro"
    return {"ancho": ANCHO, "alto": ALTO, "terreno": terreno}


def _interpretacion(estado: dict, bando: str, yo=None) -> InterpretacionJuego:
    """Reconstruye propiedades y relaciones según el bando que evalúa."""
    vivas = estado["unidades"]
    relaciones = {p: set() for p in LENGUAJE.predicados}
    for unidad in vivas:
        propiedades = (
            ("Mio", unidad["bando"] == bando), ("Enemigo", unidad["bando"] != bando),
            ("Herido", unidad["vida"] < unidad["vida_max"] / 2), (unidad["tipo"], True),
            ("EnAgua", estado["mapa"]["terreno"][unidad["fila"]][unidad["col"]] == "agua"),
        )
        for nombre, cumple in propiedades:
            if cumple:
                relaciones[nombre].add((unidad["id"],))
    for primera in vivas:
        for segunda in vivas:
            if primera["id"] == segunda["id"]:
                continue
            pareja = (primera["id"], segunda["id"])
            if distancia(primera, segunda) == 1:
                relaciones["Cerca"].add(pareja)
            if primera["col"] == segunda["col"] or primera["fila"] == segunda["fila"]:
                relaciones["Alineado"].add(pareja)
    return InterpretacionJuego([u["id"] for u in vivas], relaciones, yo or "")


def distancia(primera: dict, segunda: dict) -> int:
    """Calcula la distancia Manhattan entre dos soldados."""
    return abs(primera["col"] - segunda["col"]) + abs(primera["fila"] - segunda["fila"])


def _unidad(estado: dict, unidad: str) -> dict:
    """Busca una unidad viva o informa que dejó de pertenecer al dominio."""
    encontrada = next((u for u in estado["unidades"] if u["id"] == unidad), None)
    if encontrada is None:
        _problema(f"La unidad '{unidad}' no está viva")
    return encontrada

