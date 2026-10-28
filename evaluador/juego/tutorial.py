"""Práctica sin efectos y retroalimentación de conjuntos exactos."""
from .formulas import _evaluar_objetivos, exigir_concepto
from .lectura import leer_formula
from .mundo import _unidad
from .niveles import datos_nivel
from .validacion import _problema, _validar_estado_completo


def retroalimentacion(estado: dict, golpea: list, objetivo: list) -> dict:
    """Explica qué unidades sobran o faltan, con una pista sobre el fuego amigo."""
    sobran = sorted(set(golpea) - set(objetivo))
    faltan = sorted(set(objetivo) - set(golpea))
    frases = []
    aliados = {u["id"] for u in estado["unidades"] if u["bando"] == estado["turno"]}
    for unidad in sobran:
        frase = f"Golpeaste a {unidad}, que no era objetivo"
        if unidad in aliados:
            frase += " y es de tu equipo"
            permitidos = datos_nivel(estado["nivel"])["predicados_permitidos"]
            if "Enemigo" in permitidos:
                frase += "; revisa si falta exigir Enemigo"
            else:
                frase += "; revisa la condición que lo incluyó"
        frases.append(frase + ".")
    if faltan:
        frases.append("Faltó golpear a " + ", ".join(faltan) + ".")
    acierto = not sobran and not faltan
    return {"acierto": acierto, "golpea": sorted(golpea), "sobran": sobran, "faltan": faltan,
            "mensaje": "¡Exacto! Seleccionaste todas y solo las unidades objetivo." if acierto
            else " ".join(frases)}


def practicar(estado: dict, nivel: int, paso: int, formula: str) -> dict:
    """Comprueba una práctica o reto sin modificar el estado ni consumir energía."""
    _validar_estado_completo(estado)
    if estado["modo"] != "tutorial" or type(nivel) is not int or nivel != estado["nivel"]:
        _problema("La práctica debe corresponder a la lección del estado")
    pasos = datos_nivel(nivel)["pasos"]
    if type(paso) is not int or not 0 <= paso < len(pasos):
        _problema("El paso debe ser un índice válido de la lección, empezando por 0")
    datos = pasos[paso]
    if datos["tipo"] not in ("practica", "reto"):
        _problema("Este paso no es una práctica ni un reto")
    from .partida import crear_estado

    escenario = crear_estado("tutorial", nivel=nivel, paso=paso)
    atacante = _unidad(escenario, "A1")
    ast, _, objetivos, afectados = _evaluar_objetivos(escenario, atacante, formula)
    if datos["tipo"] == "reto":
        exigir_concepto(escenario, ast)
    respuesta = retroalimentacion(escenario, [o["id"] for o in afectados], datos["objetivo"])
    return {"ok": True, **respuesta, "lectura": leer_formula(ast),
            "estado": escenario, "objetivos": objetivos}
