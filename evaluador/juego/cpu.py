"""Movimiento de la CPU y selección de fórmulas según dificultad."""
from evaluador.errores import ErrorValidacion

from .formulas import _evaluar_objetivos
from .mundo import _unidad
from .reglas import atacar, posiciones_alcanzables
from .tipos import CONFIG_TIPOS


def _plantillas(atacante: dict) -> list[str]:
    """Propone fórmulas legibles de daño o de curación."""
    if atacante["tipo"] == "Medico":
        return ["(Mio(x) & Herido(x))", "Mio(x)",
                "(Herido(x) & (Mio(x) | Enemigo(x)))"]
    return [
        "Enemigo(x)", "(Enemigo(x) & Herido(x))",
        "(Enemigo(x) & exists y (Cerca(x,y) & Mio(y)))",
        "(Enemigo(x) & forall y (Mio(y) -> Alineado(x,y)))",
    ]


def _mover_cpu(estado: dict) -> list[dict]:
    """Acerca cada soldado al rival con un desempate estable."""
    eventos = []
    rivales = [u for u in estado["unidades"] if u["bando"] == "azul"]
    if not rivales:
        return eventos
    for unidad in estado["unidades"]:
        if unidad["bando"] != "rojo" or unidad["movio"]:
            continue
        opciones = posiciones_alcanzables(estado, unidad["id"])

        def prioridad(posicion):
            """Ordena por cercanía al rival, avance y coordenadas."""
            distancia = min(abs(posicion[0] - v["col"]) + abs(posicion[1] - v["fila"]) for v in rivales)
            return distancia, -opciones[posicion], posicion[1], posicion[0]

        destino = min(opciones, key=prioridad)
        origen = [unidad["col"], unidad["fila"]]
        if list(destino) != origen:
            unidad["col"], unidad["fila"] = destino
            unidad["movio"] = True
            eventos.append({"tipo": "mover", "unidad": unidad["id"],
                            "origen": origen, "destino": list(destino)})
    return eventos


def _candidatas(estado: dict, atacante: dict) -> list[dict]:
    """Puntúa efectos reales y descarta curaciones perjudiciales o dominadas."""
    candidatas = []
    medico = atacante["tipo"] == "Medico"
    for formula in _plantillas(atacante):
        try:
            _, costo, _, objetivos = _evaluar_objetivos(estado, atacante, formula)
        except ErrorValidacion:
            continue
        if costo > estado["energia"]["rojo"] or not objetivos:
            continue
        aliados = {o["id"] for o in objetivos if o["aliado"]}
        enemigos = {o["id"] for o in objetivos if not o["aliado"]}
        if medico:
            poder = CONFIG_TIPOS["Medico"]["poder"]
            puntaje = sum(
                min(poder, _unidad(estado, i)["vida_max"] - _unidad(estado, i)["vida"])
                for i in aliados
            ) - 100 * len(enemigos)
        else:
            puntaje = 3 * len(enemigos) - 5 * len(aliados)
        if puntaje > 0:
            candidatas.append({"puntaje": puntaje, "formula": formula,
                               "aliados": aliados, "enemigos": enemigos})
    if medico:
        candidatas = [
            candidata for candidata in candidatas
            if not any(
                otra["aliados"] >= candidata["aliados"]
                and otra["enemigos"] < candidata["enemigos"]
                for otra in candidatas
            )
        ]
    return sorted(candidatas, key=lambda c: (-c["puntaje"], c["formula"]))


def _cpu_actuar(estado: dict, rng) -> tuple[dict, list]:
    """Ejecuta el movimiento y los ataques conservando el estado de cada acción."""
    eventos = _mover_cpu(estado)
    ids = [u["id"] for u in estado["unidades"] if u["bando"] == "rojo"]
    for unidad_id in ids:
        atacante = next((u for u in estado["unidades"] if u["id"] == unidad_id), None)
        if atacante is None or atacante["ataco"]:
            continue
        candidatas = _candidatas(estado, atacante)
        if not candidatas:
            continue
        dificultad = estado["dificultad"]["rojo"]
        if dificultad == "facil":
            elegida = rng.choice(candidatas)
        elif dificultad == "normal":
            elegida = rng.choice(candidatas[:3])
        else:
            elegida = candidatas[0]
        respuesta = atacar(estado, unidad_id, elegida["formula"])
        estado = respuesta["estado"]
        eventos.extend(respuesta["eventos"])
        if estado["ganador"]:
            break
    return estado, eventos
