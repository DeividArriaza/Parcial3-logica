"""Sintaxis, vocabulario, costo y selección de objetivos con el evaluador real."""
from evaluador.errores import Categoria
from evaluador.semantica import Evaluador
from evaluador.sintaxis import (
    Aplicacion, Binaria, Cuantificador, Igualdad, Negacion, Predicado,
    analizar, variables_libres,
)

from .mundo import _interpretacion
from .niveles import datos_nivel
from .tipos import CONFIG_TIPOS, COSTO_BASE, COSTO_CONECTIVO, COSTO_CUANTIFICADOR, LENGUAJE
from .validacion import _problema

LONGITUD_MAXIMA = 300


def analizar_formula(texto: str):
    """Limita la entrada y convierte la recursión excesiva en un error explicable."""
    if not isinstance(texto, str):
        _problema("La fórmula debe ser texto", Categoria.SINTAXIS)
    if len(texto) > LONGITUD_MAXIMA:
        _problema(f"La fórmula admite como máximo {LONGITUD_MAXIMA} caracteres", Categoria.SINTAXIS)
    try:
        return analizar(texto, LENGUAJE)
    except RecursionError:
        _problema("La fórmula tiene demasiados niveles de anidación", Categoria.SINTAXIS)


def _costo(ast) -> int:
    """Suma el costo base y el de cada operador del árbol."""
    if isinstance(ast, Negacion):
        return COSTO_CONECTIVO + _costo(ast.subformula)
    if isinstance(ast, Binaria):
        return COSTO_CONECTIVO + _costo(ast.izquierda) + _costo(ast.derecha) - COSTO_BASE
    if isinstance(ast, Cuantificador):
        return COSTO_CUANTIFICADOR + _costo(ast.cuerpo)
    return COSTO_BASE


def _simbolos_ast(ast) -> set[str]:
    """Extrae predicados, constantes y operadores, incluida la igualdad."""
    if isinstance(ast, Predicado):
        return {ast.nombre} | set().union(*(_simbolos_termino(t) for t in ast.argumentos))
    if isinstance(ast, Igualdad):
        return {"="} | _simbolos_termino(ast.izquierda) | _simbolos_termino(ast.derecha)
    if isinstance(ast, Negacion):
        return {"¬"} | _simbolos_ast(ast.subformula)
    if isinstance(ast, Binaria):
        return {ast.conectivo} | _simbolos_ast(ast.izquierda) | _simbolos_ast(ast.derecha)
    if isinstance(ast, Cuantificador):
        return {ast.cuantificador} | _simbolos_ast(ast.cuerpo)
    return set()


def _simbolos_termino(termino) -> set[str]:
    """Recoge constantes y funciones sin confundirlas con variables."""
    if isinstance(termino, Aplicacion):
        return {termino.funcion} | set().union(*(_simbolos_termino(t) for t in termino.argumentos))
    return set()


def exigir_concepto(estado: dict, ast) -> None:
    """Exige el símbolo que enseña el reto, aunque una selección accidental coincida."""
    if estado.get("modo") != "tutorial":
        return
    datos = datos_nivel(estado["nivel"])
    paso = estado.get("paso_tutorial", len(datos["pasos"]) - 1)
    if datos["pasos"][paso]["tipo"] != "reto":
        _problema("Este es un paso guiado: usa Comprobar y reserva el ataque real para el reto")
    if datos["simbolo_nuevo"] not in _simbolos_ast(ast):
        _problema("En este reto debes usar el símbolo nuevo: " + datos["simbolo_nuevo"],
                  Categoria.SIMBOLO)


def _formula(estado, texto, bando, atacante=None):
    """Valida el vocabulario de la lección y permite únicamente x libre."""
    ast = analizar_formula(texto)
    try:
        if estado.get("modo") == "tutorial":
            nivel = datos_nivel(estado["nivel"])
            permitidos = set(nivel["simbolos_permitidos"] + nivel["predicados_permitidos"])
            prohibidos = _simbolos_ast(ast) - permitidos
            if prohibidos:
                _problema("Este nivel no permite estos símbolos: " + ", ".join(sorted(prohibidos)),
                          Categoria.SIMBOLO)
        libres = [v for v in variables_libres(ast) if v != "x"]
        if libres:
            _problema("La única variable libre permitida es 'x'; encontradas: " + ", ".join(libres),
                      Categoria.ASIGNACION)
        return ast, Evaluador(_interpretacion(estado, bando, atacante)), _costo(ast)
    except RecursionError:
        _problema("La fórmula tiene demasiados niveles de anidación", Categoria.SINTAXIS)


def _evaluar_objetivos(estado, atacante, texto):
    """Evalúa cada soldado vivo e incluye las razones y el alcance por separado."""
    ast, evaluador, costo = _formula(estado, texto, atacante["bando"], atacante["id"])
    objetivos = []
    try:
        for unidad in estado["unidades"]:
            arbol = evaluador.evaluar(ast, {"x": unidad["id"]})
            distancia = abs(unidad["col"] - atacante["col"]) + abs(unidad["fila"] - atacante["fila"])
            en_alcance = (
                unidad["id"] != atacante["id"]
                and distancia <= CONFIG_TIPOS[atacante["tipo"]]["alcance"]
            )
            objetivos.append({
                "id": unidad["id"], "cumple": arbol.valor, "en_alcance": en_alcance,
                "afectado": arbol.valor and en_alcance,
                "aliado": unidad["bando"] == atacante["bando"],
                "efecto": "cura" if atacante["tipo"] == "Medico" else "danio",
                "arbol": arbol.como_dict(),
            })
    except RecursionError:
        _problema("La fórmula tiene demasiados niveles de anidación", Categoria.SINTAXIS)
    afectados = [o for o in objetivos if o["afectado"]]
    return ast, costo, objetivos, afectados

