"""Validación del estado serializado y de las condiciones para actuar."""
from evaluador.errores import Categoria, ErrorValidacion

from .niveles import datos_nivel
from .tipos import (
    ALTO, ANCHO, CONFIG_TIPOS, COSTO_BASE, COSTO_CONECTIVO,
    COSTO_CUANTIFICADOR, ENERGIA_MAXIMA,
)


def _problema(mensaje: str, categoria=Categoria.DOMINIO):
    """Comunica una infracción de reglas con el formato del evaluador."""
    raise ErrorValidacion.uno(categoria, mensaje)


def _validar_estado_completo(estado: dict) -> None:
    """Valida también estados terminales; actuar exige una comprobación adicional."""
    obligatorios = {
        "modo", "turno", "numero_turno", "energia", "dificultad",
        "mapa", "unidades", "ganador", "costo", "tipos",
    }
    if not isinstance(estado, dict) or not obligatorios <= estado.keys():
        _problema("Falta un estado de juego válido o campos obligatorios")
    if estado["modo"] not in ("cpu", "local", "tutorial") or estado["turno"] not in ("azul", "rojo"):
        _problema("El estado contiene un modo o turno inválido")
    if type(estado["numero_turno"]) is not int or estado["numero_turno"] < 1:
        _problema("El número de turno debe ser un entero positivo")
    costo = {"base": COSTO_BASE, "por_conectivo": COSTO_CONECTIVO,
             "por_cuantificador": COSTO_CUANTIFICADOR}
    if estado["costo"] != costo or estado["tipos"] != CONFIG_TIPOS:
        _problema("El estado contiene parámetros de costo o tipos inválidos")
    if estado["ganador"] not in (None, "azul", "rojo"):
        _problema("El estado contiene un ganador inválido")
    if estado.get("semilla") is not None and type(estado["semilla"]) is not int:
        _problema("La semilla debe ser un entero")
    _validar_recursos(estado)
    _validar_mapa(estado["mapa"])
    _validar_unidades(estado)
    _validar_resultado(estado)


def _validar_recursos(estado: dict) -> None:
    """Comprueba energía y dificultad para ambos bandos."""
    energia = estado["energia"]
    if not isinstance(energia, dict) or not {"azul", "rojo"} <= energia.keys():
        _problema("La energía debe declarar ambos bandos")
    for bando in ("azul", "rojo"):
        if type(energia[bando]) is not int or not 0 <= energia[bando] <= ENERGIA_MAXIMA:
            _problema(f"La energía debe estar entre 0 y {ENERGIA_MAXIMA}")
    dificultad = estado["dificultad"]
    if not isinstance(dificultad, dict):
        _problema("La dificultad debe declarar ambos bandos")
    if any(dificultad.get(b) not in ("facil", "normal", "dificil") for b in ("azul", "rojo")):
        _problema("El estado contiene una dificultad inválida")


def _validar_mapa(mapa: dict) -> None:
    """Comprueba dimensiones y terrenos admitidos."""
    if not isinstance(mapa, dict) or mapa.get("ancho") != ANCHO or mapa.get("alto") != ALTO:
        _problema(f"El mapa debe medir {ANCHO} por {ALTO}")
    terreno = mapa.get("terreno")
    if not isinstance(terreno, list) or len(terreno) != ALTO:
        _problema("El terreno debe tener una fila por cada fila del tablero")
    for fila in terreno:
        if not isinstance(fila, list) or len(fila) != ANCHO:
            _problema("Cada fila del terreno debe tener el ancho del tablero")
        if any(celda not in ("pasto", "agua", "muro") for celda in fila):
            _problema("El terreno solo admite pasto, agua y muro")


def _validar_unidades(estado: dict) -> None:
    """Rechaza unidades inválidas, repetidas, superpuestas o sobre muros."""
    unidades = estado["unidades"]
    if not isinstance(unidades, list) or not unidades or len(unidades) > ANCHO * ALTO:
        _problema("El estado debe contener una lista no vacía de unidades dentro del tablero")
    ids, posiciones = set(), set()
    campos = {"id", "bando", "tipo", "col", "fila", "vida", "vida_max", "movio", "ataco"}
    for unidad in unidades:
        if not isinstance(unidad, dict) or not campos <= unidad.keys():
            _problema("Cada unidad debe contener todos los campos obligatorios")
        _validar_unidad(unidad)
        posicion = (unidad["col"], unidad["fila"])
        if unidad["id"] in ids or posicion in posiciones:
            _problema("El estado contiene ids o posiciones repetidas")
        if estado["mapa"]["terreno"][unidad["fila"]][unidad["col"]] == "muro":
            _problema(f"La unidad {unidad['id']} está sobre un muro")
        ids.add(unidad["id"])
        posiciones.add(posicion)


def _validar_unidad(unidad: dict) -> None:
    """Valida identidad, coordenadas, vida e indicadores de una unidad."""
    if not isinstance(unidad["id"], str) or not unidad["id"].strip():
        _problema("Cada unidad debe tener un id de texto no vacío")
    if unidad["bando"] not in ("azul", "rojo"):
        _problema("El estado contiene un bando de unidad inválido")
    if not isinstance(unidad["tipo"], str) or unidad["tipo"] not in CONFIG_TIPOS:
        _problema("El estado contiene un tipo de unidad inválido")
    col, fila = unidad["col"], unidad["fila"]
    if type(col) is not int or type(fila) is not int or not (0 <= col < ANCHO and 0 <= fila < ALTO):
        _problema(f"Las coordenadas de {unidad['id']} están fuera del tablero")
    maximo = CONFIG_TIPOS[unidad["tipo"]]["vida"]
    if type(unidad["vida_max"]) is not int or unidad["vida_max"] != maximo:
        _problema("La vida máxima debe coincidir con el tipo de unidad")
    if type(unidad["vida"]) is not int or not 1 <= unidad["vida"] <= maximo:
        _problema(f"La vida de {unidad['id']} debe estar entre 1 y {maximo}")
    if type(unidad["movio"]) is not bool or type(unidad["ataco"]) is not bool:
        _problema("Los indicadores de las unidades deben ser booleanos")


def _validar_resultado(estado: dict) -> None:
    """Comprueba victoria por eliminación o resultado exacto del tutorial."""
    bandos = {u["bando"] for u in estado["unidades"]}
    if estado["modo"] == "tutorial":
        _validar_tutorial(estado)
        if estado["ganador"] != ("azul" if estado["nivel_completado"] else None):
            _problema("El ganador no coincide con el resultado de la lección")
        if bandos != {"azul", "rojo"} and not (
            estado["nivel_completado"] or estado.get("nivel_fallido", False)
        ):
            _problema("Una partida sin un bando debe declarar su resultado")
        return
    esperado = None if len(bandos) == 2 else next(iter(bandos))
    if estado["ganador"] != esperado:
        _problema("El ganador no coincide con los bandos que siguen vivos")


def _validar_tutorial(estado: dict) -> None:
    """Valida metas incluso si el ataque ya eliminó objetivos o señuelos."""
    numero = estado.get("nivel")
    if type(numero) is not int or numero not in range(9):
        _problema("El nivel tutorial debe estar entre 0 y 8")
    datos = datos_nivel(numero)
    paso = estado.get("paso_tutorial", len(datos["pasos"]) - 1)
    if type(paso) is not int or not 0 <= paso < len(datos["pasos"]):
        _problema("El paso del estado no corresponde a la lección")
    if estado.get("objetivos_nivel") != datos["pasos"][paso].get("objetivo", []):
        _problema("Los objetivos no corresponden a la lección")
    for campo in ("nivel_completado", "nivel_fallido"):
        defecto = None if campo == "nivel_completado" else False
        if type(estado.get(campo, defecto)) is not bool:
            _problema(f"El campo {campo} debe ser booleano")
    if estado.get("nivel_completado") and estado.get("nivel_fallido"):
        _problema("Una lección no puede estar completada y fallida")
    if not estado.get("nivel_completado") and not estado.get("nivel_fallido"):
        ids = {u["id"] for u in estado["unidades"]}
        if not set(estado["objetivos_nivel"]) <= ids or "A1" not in ids:
            _problema("Faltan unidades necesarias para el reto")


def _validar_activa(estado: dict) -> None:
    """Rechaza acciones en partidas terminadas sin invalidar el estado terminal."""
    _validar_estado_completo(estado)
    if estado["ganador"]:
        _problema("La partida ya terminó")
    if estado.get("nivel_fallido"):
        _problema("La lección falló. Reintenta creando una partida del mismo nivel.")

