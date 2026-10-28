"""Movimiento, ataques, efectos y cambios de turno del juego."""
from collections import deque
from copy import deepcopy
import random

from evaluador.errores import Categoria

from .formulas import _evaluar_objetivos
from .lectura import leer_formula
from .mundo import _unidad
from .tipos import CONFIG_TIPOS, ENERGIA_MAXIMA, ENERGIA_POR_TURNO
from .validacion import _problema, _validar_activa


def _atacante(estado: dict, unidad_id: str) -> dict:
    """Comprueba el turno, los usos del ataque y el atacante fijado para el reto."""
    _validar_activa(estado)
    atacante = _unidad(estado, unidad_id)
    if atacante["bando"] != estado["turno"]:
        _problema("Solo puede atacar una unidad del bando en turno")
    if atacante["ataco"]:
        _problema("Esta unidad ya atacó durante este turno")
    if estado["modo"] == "tutorial" and unidad_id != "A1":
        _problema("El reto debe resolverse con el atacante A1")
    return atacante


def _detalle(estado: dict, bando: str) -> str:
    """Determina cuánto revelar según la dificultad y el modo."""
    dificultad = "facil" if estado["modo"] == "tutorial" else estado["dificultad"][bando]
    return {"facil": "completo", "normal": "conteo", "dificil": "sintaxis"}[dificultad]


def _exigir_energia(estado: dict, bando: str, costo: int) -> None:
    """Rechaza ataques cuya fórmula excede la energía disponible."""
    energia = estado["energia"][bando]
    if costo > energia:
        _problema(f"Energía insuficiente: la fórmula cuesta {costo} y tienes {energia}",
                  Categoria.ASIGNACION)


def _precision(cantidad: int) -> int:
    """Premia seleccionar uno o dos objetivos."""
    return {1: 2, 2: 1}.get(cantidad, 0)


def previsualizar(estado: dict, atacante_id: str, texto: str) -> dict:
    """Valida y anticipa el ataque sin gastar energía ni modificar el estado."""
    atacante = _atacante(estado, atacante_id)
    ast, costo, objetivos, afectados = _evaluar_objetivos(estado, atacante, texto)
    _exigir_energia(estado, atacante["bando"], costo)
    detalle = _detalle(estado, atacante["bando"])
    bonus = _precision(len(afectados))
    for objetivo in objetivos:
        unidad = _unidad(estado, objetivo["id"])
        cantidad = 0
        medico = atacante["tipo"] == "Medico"
        if objetivo["afectado"]:
            poder = CONFIG_TIPOS[atacante["tipo"]]["poder"]
            cantidad = min(poder, unidad["vida_max"] - unidad["vida"]) if medico else poder + bonus
        objetivo["cantidad"] = cantidad
        objetivo["vida_resultado"] = unidad["vida"] + (cantidad if medico else -cantidad)
        objetivo["baja"] = not medico and objetivo["vida_resultado"] <= 0
    resumen = {"enemigos": 0, "aliados": 0}
    if detalle != "sintaxis":
        resumen = {"enemigos": sum(not o["aliado"] for o in afectados),
                   "aliados": sum(o["aliado"] for o in afectados)}
    return {
        "ok": True, "costo": costo, "energia": estado["energia"][atacante["bando"]],
        "nivel_detalle": detalle, "resumen": resumen,
        "objetivos": objetivos if detalle == "completo" else [], "lectura": leer_formula(ast),
    }


def atacar(estado: dict, atacante_id: str, texto: str) -> dict:
    """Ejecuta un ataque y decide la victoria o el resultado exacto del reto."""
    estado = deepcopy(estado)
    atacante = _atacante(estado, atacante_id)
    _, costo, objetivos, afectados = _evaluar_objetivos(estado, atacante, texto)
    bando = atacante["bando"]
    _exigir_energia(estado, bando, costo)
    estado["energia"][bando] -= costo
    atacante["ataco"] = True
    eventos = [{"tipo": "ataque", "atacante": atacante_id, "formula": texto, "costo": costo}]
    resultado = {}
    if estado["modo"] == "tutorial":
        from .tutorial import retroalimentacion

        resultado = retroalimentacion(estado, [o["id"] for o in afectados], estado["objetivos_nivel"])
    _aplicar_efectos(estado, atacante, afectados, eventos)
    if estado["modo"] == "tutorial":
        estado["nivel_completado"] = resultado["acierto"]
        estado["nivel_fallido"] = not resultado["acierto"]
        estado["mensaje_nivel"] = resultado["mensaje"]
        estado["sobran"], estado["faltan"] = resultado["sobran"], resultado["faltan"]
        estado["ganador"] = "azul" if resultado["acierto"] else None
        eventos.append({"tipo": "mensaje", "mensaje": resultado["mensaje"]})
    else:
        bandos = {u["bando"] for u in estado["unidades"]}
        estado["ganador"] = next(iter(bandos)) if len(bandos) == 1 else None
    if estado["ganador"]:
        eventos.append({"tipo": "victoria", "bando": estado["ganador"]})
    return {
        "ok": True, "estado": estado, "eventos": eventos, **resultado,
        "objetivos": objetivos if _detalle(estado, bando) == "completo" else [],
    }


def _aplicar_efectos(estado: dict, atacante: dict, afectados: list, eventos: list) -> None:
    """Cura o daña a todos los seleccionados y retira las bajas del dominio."""
    poder = CONFIG_TIPOS[atacante["tipo"]]["poder"]
    for objetivo in afectados:
        unidad = _unidad(estado, objetivo["id"])
        if atacante["tipo"] == "Medico":
            cantidad = min(poder, unidad["vida_max"] - unidad["vida"])
            unidad["vida"] += cantidad
            eventos.append({"tipo": "cura", "unidad": unidad["id"], "cantidad": cantidad})
        else:
            cantidad = poder + _precision(len(afectados))
            unidad["vida"] -= cantidad
            eventos.append({"tipo": "danio", "unidad": unidad["id"], "cantidad": cantidad})
            if unidad["vida"] <= 0:
                eventos.append({"tipo": "baja", "unidad": unidad["id"]})
    estado["unidades"] = [u for u in estado["unidades"] if u["vida"] > 0]
    if not afectados:
        eventos.append({"tipo": "mensaje", "mensaje": "Nadie cumplió; se gastó la energía."})


def posiciones_alcanzables(estado: dict, unidad_id: str) -> dict:
    """Relaja caminos de costo ponderado respetando agua, muros y ocupación."""
    unidad = _unidad(estado, unidad_id)
    mapa = estado["mapa"]
    terreno = mapa["terreno"]
    ocupadas = {(u["col"], u["fila"]) for u in estado["unidades"] if u["id"] != unidad_id}
    origen = (unidad["col"], unidad["fila"])
    distancias = {origen: 0}
    cola = deque([origen])
    while cola:
        col, fila = cola.popleft()
        for x, y in ((col + 1, fila), (col - 1, fila), (col, fila + 1), (col, fila - 1)):
            if not (0 <= x < mapa["ancho"] and 0 <= y < mapa["alto"]):
                continue
            if (x, y) in ocupadas or terreno[y][x] == "muro":
                continue
            costo = distancias[col, fila] + (2 if terreno[y][x] == "agua" else 1)
            if costo <= CONFIG_TIPOS[unidad["tipo"]]["mov"] and costo < distancias.get((x, y), 999):
                distancias[x, y] = costo
                cola.append((x, y))
    return distancias


def mover(estado: dict, unidad_id: str, destino) -> dict:
    """Mueve una unidad una vez por turno a una casilla alcanzable."""
    estado = deepcopy(estado)
    _validar_activa(estado)
    unidad = _unidad(estado, unidad_id)
    if unidad["bando"] != estado["turno"]:
        _problema("Solo puede moverse una unidad del bando en turno")
    if unidad["movio"]:
        _problema("Esta unidad ya se movió durante este turno")
    if not isinstance(destino, (list, tuple)) or len(destino) != 2:
        _problema("El destino debe ser [columna, fila]")
    if any(type(valor) is not int for valor in destino):
        _problema("El destino debe contener enteros")
    posicion = tuple(destino)
    distancias = posiciones_alcanzables(estado, unidad_id)
    origen = [unidad["col"], unidad["fila"]]
    if posicion not in distancias or list(destino) == origen:
        _problema("Destino no alcanzable: revisa el terreno, ocupación y puntos de movimiento")
    unidad["col"], unidad["fila"] = posicion
    unidad["movio"] = True
    return {"ok": True, "estado": estado, "evento": {
        "tipo": "mover", "unidad": unidad_id, "origen": origen, "destino": list(destino),
        "costo_movimiento": distancias[posicion],
    }}


def _cambiar_turno(estado: dict) -> None:
    """Recarga energía y habilita las unidades del siguiente bando."""
    turno = "rojo" if estado["turno"] == "azul" else "azul"
    estado["turno"] = turno
    estado["numero_turno"] += 1
    estado["energia"][turno] = min(ENERGIA_MAXIMA, estado["energia"][turno] + ENERGIA_POR_TURNO)
    for unidad in estado["unidades"]:
        if unidad["bando"] == turno:
            unidad["movio"], unidad["ataco"] = False, False


def terminar_turno(estado: dict) -> dict:
    """Pasa el turno y ejecuta la CPU cuando corresponde."""
    from .cpu import _cpu_actuar

    estado = deepcopy(estado)
    _validar_activa(estado)
    if estado["modo"] == "tutorial":
        _problema("Resuelve el reto con un ataque de A1 o reintenta la lección")
    _cambiar_turno(estado)
    eventos = []
    if estado["modo"] == "cpu" and estado["turno"] == "rojo":
        estado, eventos = _cpu_actuar(estado, random.Random(estado.get("semilla")))
        if not estado["ganador"]:
            _cambiar_turno(estado)
    return {"ok": True, "estado": estado, "eventos": eventos}

