"""Lectura compositiva en español de los términos y fórmulas del juego."""
from evaluador.errores import Categoria
from evaluador.sintaxis import Aplicacion, Binaria, Cuantificador, Igualdad, Negacion, Predicado

from .validacion import _problema


def _termino(termino) -> str:
    """Nombra la constante del atacante y conserva los nombres de las variables."""
    if isinstance(termino, Aplicacion):
        if termino.funcion == "yo":
            return "el atacante"
        argumentos = ", ".join(_termino(a) for a in termino.argumentos)
        return termino.funcion if not argumentos else f"{termino.funcion} de {argumentos}"
    return termino.nombre


def _predicado(ast, negado=False) -> str:
    """Lee propiedades y relaciones con concordancia y negación natural."""
    sujetos = [_termino(t) for t in ast.argumentos]
    sujeto = sujetos[0]
    no = "no " if negado else ""
    propiedades = {
        "Mio": "es de tu equipo", "Enemigo": "es enemigo", "Herido": "está herido",
        "Infante": "es infante", "Arquero": "es arquero", "Medico": "es médico",
        "Tanque": "es tanque", "EnAgua": "está en el agua",
    }
    if ast.nombre in propiedades:
        return f"{sujeto} {no}{propiedades[ast.nombre]}"
    relacion = "está cerca de" if ast.nombre == "Cerca" else "está alineado con"
    if ast.nombre == "Cerca" and sujetos[1] == "el atacante":
        return f"{sujeto} {no}está cerca del atacante"
    return f"{sujeto} {no}{relacion} {sujetos[1]}"


def _leer(ast) -> str:
    """Combina las lecturas de todos los nodos preservando su agrupación."""
    if isinstance(ast, Predicado):
        return _predicado(ast)
    if isinstance(ast, Igualdad):
        return f"{_termino(ast.izquierda)} es el mismo soldado que {_termino(ast.derecha)}"
    if isinstance(ast, Negacion):
        if isinstance(ast.subformula, Predicado):
            return _predicado(ast.subformula, negado=True)
        return "no se cumple que (" + _leer(ast.subformula) + ")"
    if isinstance(ast, Binaria):
        izquierda, derecha = _leer(ast.izquierda), _leer(ast.derecha)
        if ast.conectivo == "→":
            return f"si ({izquierda}), entonces ({derecha})"
        enlace = "y" if ast.conectivo == "∧" else "o"
        return f"({izquierda}) {enlace} ({derecha})"
    if isinstance(ast, Cuantificador):
        if ast.cuantificador == "∃":
            return f"existe algún soldado {ast.variable} para el que ({_leer(ast.cuerpo)})"
        return f"para cada soldado {ast.variable}, se cumple ({_leer(ast.cuerpo)})"
    _problema("No se puede leer este nodo de fórmula", Categoria.SINTAXIS)


def leer_formula(formula) -> str:
    """Traduce texto o un AST a español sin cambiar el significado de su agrupación."""
    from .formulas import analizar_formula

    ast = analizar_formula(formula) if isinstance(formula, str) else formula
    try:
        return _leer(ast)
    except RecursionError:
        _problema("La fórmula tiene demasiados niveles de anidación", Categoria.SINTAXIS)
