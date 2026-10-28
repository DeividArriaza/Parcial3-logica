"""Creación de partidas y preparación de los encuentros tutoriales."""
from copy import deepcopy

from .mundo import _mapa
from .niveles import _unidades_nivel, datos_nivel
from .tipos import (
    CONFIG_TIPOS, COSTO_BASE, COSTO_CONECTIVO, COSTO_CUANTIFICADOR,
    ENERGIA_INICIAL,
)
from .validacion import _problema


def crear_estado(modo="cpu", dificultad=None, nivel=None, semilla=None, paso=None) -> dict:
    """Crea una partida independiente con parámetros de balance públicos."""
    if modo not in ("cpu", "local", "tutorial"):
        _problema("El modo debe ser cpu, local o tutorial")
    if dificultad is None:
        dificultad = {}
    if not isinstance(dificultad, dict):
        _problema("La dificultad debe indicar azul y rojo")
    dificultad = {b: dificultad.get(b, "normal") for b in ("azul", "rojo")}
    if any(v not in ("facil", "normal", "dificil") for v in dificultad.values()):
        _problema("La dificultad debe ser facil, normal o dificil")
    if semilla is not None and type(semilla) is not int:
        _problema("La semilla debe ser un entero")
    mapa = _mapa()
    objetivos = None
    if modo == "tutorial":
        nivel = 0 if nivel is None else nivel
        if type(nivel) is not int or nivel not in range(9):
            _problema("El nivel tutorial debe ser un entero entre 0 y 8")
        datos = datos_nivel(nivel)
        paso = len(datos["pasos"]) - 1 if paso is None else paso
        if type(paso) is not int or not 0 <= paso < len(datos["pasos"]):
            _problema("El paso debe ser un índice válido de la lección, empezando por 0")
        unidades = _unidades_nivel(nivel, paso)
        objetivos = datos["pasos"][paso].get("objetivo", [])
        mapa["terreno"] = [["pasto"] * mapa["ancho"] for _ in range(mapa["alto"])]
    else:
        nivel = None
        paso = None
        unidades = _equipos()
    return {
        "modo": modo, "turno": "azul", "numero_turno": 1,
        "energia": {"azul": ENERGIA_INICIAL, "rojo": ENERGIA_INICIAL},
        "dificultad": dificultad, "mapa": mapa, "unidades": unidades,
        "ganador": None, "nivel": nivel, "paso_tutorial": paso, "objetivos_nivel": objetivos,
        "nivel_completado": False, "nivel_fallido": False, "mensaje_nivel": "",
        "sobran": [], "faltan": [], "semilla": semilla,
        "costo": {"base": COSTO_BASE, "por_conectivo": COSTO_CONECTIVO,
                  "por_cuantificador": COSTO_CUANTIFICADOR},
        "tipos": deepcopy(CONFIG_TIPOS),
    }


def _equipos() -> list[dict]:
    """Coloca una unidad de cada tipo por bando para el juego libre."""
    unidades = []
    for bando, prefijo, col in (("azul", "A", 1), ("rojo", "R", 8)):
        for indice, tipo in enumerate(CONFIG_TIPOS):
            vida = CONFIG_TIPOS[tipo]["vida"]
            unidades.append({
                "id": f"{prefijo}{indice + 1}", "bando": bando, "tipo": tipo,
                "col": col, "fila": indice * 2, "vida": vida, "vida_max": vida,
                "movio": False, "ataco": False,
            })
    return unidades

