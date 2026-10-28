"""Nueve lecciones guiadas y encuentros que exigen el concepto presentado."""
from copy import deepcopy

from .tipos import CONFIG_TIPOS


def _leccion(numero, titulo, simbolos, predicados, nuevo, objetivos, solucion, texto, plantilla):
    """Declara vocabulario, pasos guiados y meta exacta de una lección."""
    objetivo = "Golpea exactamente a " + ", ".join(objetivos) + " con A1 en un ataque."
    pistas = [texto, "Completa esta estructura: " + plantilla, solucion]
    pasos = [
        {"tipo": "explicacion", "titulo": titulo, "texto": texto,
         "resaltar": objetivos, "simbolo": nuevo},
        {"tipo": "ejemplo", "titulo": "Revisemos juntos", "formula": solucion,
         "comentar": ["R1", "A2"]},
        {"tipo": "practica", "titulo": "Ahora prueba tú", "plantilla": plantilla,
         "objetivo": objetivos, "pistas": pistas, "solucion": solucion},
        {"tipo": "reto", "titulo": "Tu ataque", "objetivo": objetivos,
         "solucion": solucion},
    ]
    return {
        "id": numero, "titulo": titulo, "descripcion": objetivo, "objetivo": objetivo,
        "simbolos": predicados + simbolos, "simbolos_permitidos": simbolos,
        "predicados_permitidos": predicados, "simbolo_nuevo": nuevo,
        "objetivos": objetivos, "atacante": "A1", "solucion_ejemplo": solucion,
        "pista": texto, "explicacion": texto, "pasos": pasos,
    }


_NIVELES = [
    _leccion(0, "El campo de batalla", [], ["Mio", "Enemigo"], "Enemigo", ["R1"],
             "Enemigo(x)",
             "El tablero es nuestro mundo. Su dominio es la lista de soldados vivos. "
             "x significa el soldado que revisamos: pasamos por cada uno. "
             "Enemigo(x) pregunta si pertenece al otro equipo.", "___(x)"),
    _leccion(1, "Predicados de tipo", [], ["Arquero", "Enemigo"], "Arquero", ["R1"],
             "Arquero(x)",
             "Un predicado es una pregunta sobre un soldado. Arquero(x) pregunta su tipo; "
             "Tanque(x), si es tanque; Herido(x), si tiene menos de la mitad de vida. "
             "Mio y Enemigo cambian de significado cuando cambia el equipo en turno.", "___(x)"),
    _leccion(2, "Negación", ["¬"], ["Herido"], "¬", ["R1"], "~Herido(x)",
             "¬ invierte la respuesta: verdadero pasa a falso y falso a verdadero. "
             "Escribe ~ o !. Selecciona al único soldado sano en alcance.", "___Herido(x)"),
    _leccion(3, "Conjunción", ["∧"], ["Enemigo", "Arquero"], "∧", ["R1"],
             "(Enemigo(x) & Arquero(x))",
             "∧ exige las dos condiciones al mismo tiempo. Escribe &. "
             "Ser arquero no basta: A2 es tuyo. Ser enemigo tampoco basta: R2 no es arquero.",
             "(Enemigo(x) ___ Arquero(x))"),
    _leccion(4, "Disyunción", ["∧", "∨"], ["Enemigo", "Infante", "Arquero"],
             "∨", ["R1", "R2"], "(Enemigo(x) & (Infante(x) | Arquero(x)))",
             "∨ acepta al menos una condición, incluso ambas. Escribe |. "
             "Reúne infantes y arqueros; después exige que sean enemigos con ∧.",
             "(Enemigo(x) & (Infante(x) ___ Arquero(x)))"),
    _leccion(5, "Implicación", ["→"], ["Herido", "Infante"], "→", ["R1", "R2"],
             "(Herido(x) -> Infante(x))",
             "→ se escribe ->. Si el soldado está herido, exige que sea infante. "
             "Si no se cumple la condición inicial, la fórmula es verdadera. "
             "R1 está sano; R2 está herido y es infante.", "(Herido(x) ___ Infante(x))"),
    _leccion(6, "Relaciones y yo", [], ["Cerca", "Alineado", "yo"], "Cerca", ["R1"],
             "Cerca(x,yo)",
             "Una relación compara dos soldados. yo es una constante: siempre nombra al atacante. "
             "Cerca(x,yo) exige una casilla de distancia; Alineado(x,yo), misma fila o columna. "
             "Ninguna de estas relaciones acepta al mismo soldado dos veces.", "___(x,yo)"),
    _leccion(7, "Existe", ["∃"], ["Cerca"], "∃", ["R1"], "exists y Cerca(x,y)",
             "∃ se escribe exists: existe al menos un y que cumple la condición. "
             "Ese soldado y es un testigo. R1 tiene un vecino fuera del alcance; "
             "el testigo no puede ser R1, porque Cerca excluye al mismo soldado.", "___ y Cerca(x,y)"),
    _leccion(8, "Para todo y anidación", ["∀", "∃", "∨"], ["Alineado", "Cerca"],
             "∀", ["R1"], "forall y exists z (Alineado(x,y) | Cerca(y,z))",
             "∀ se escribe forall: la condición debe funcionar para cada y. "
             "Busca un vecino z para cada y, o exige alineación con x. "
             "Las dos unidades aisladas obligan a alinear x con ambas. "
             "∀y∃z permite un testigo distinto para cada y; ∃z∀y exige un único testigo para todos. "
             "Si un y no cumple, es un contraejemplo.",
             "___ y exists z (Alineado(x,y) | Cerca(y,z))"),
]

# La tabla conserva el orden condición inicial, consecuencia, resultado.
_NIVELES[5]["tabla_verdad"] = [
    {"antecedente": a, "consecuente": b, "resultado": not a or b}
    for a, b in [(False, False), (False, True), (True, False), (True, True)]
]
_NIVELES[5]["pasos"][0]["tabla_verdad"] = _NIVELES[5]["tabla_verdad"]


def niveles() -> list[dict]:
    """Entrega copias de lecciones y lecturas de sus ejemplos sin ciclos de importación."""
    from .lectura import leer_formula

    salida = deepcopy(_NIVELES)
    for nivel in salida:
        for paso in nivel["pasos"]:
            if paso["tipo"] == "ejemplo":
                paso["lectura"] = leer_formula(paso["formula"])
    return salida


def datos_nivel(numero: int) -> dict:
    """Consulta la declaración interna sin calcular lecturas ni modificarla."""
    return deepcopy(_NIVELES[numero])


def _unidad(nombre, bando, tipo, col, fila, vida=None) -> dict:
    """Construye una unidad coherente con los parámetros de su tipo."""
    maxima = CONFIG_TIPOS[tipo]["vida"]
    return {"id": nombre, "bando": bando, "tipo": tipo, "col": col, "fila": fila,
            "vida": maxima if vida is None else vida, "vida_max": maxima,
            "movio": False, "ataco": False}


def _unidades_nivel(numero: int) -> list[dict]:
    """Coloca objetivos y señuelos; la partida prepara terreno transitable debajo."""
    atacante = _unidad("A1", "azul", "Arquero", 1, 4, 2)
    aliado = _unidad("A2", "azul", "Tanque", 1, 2, 2)
    if numero == 0:
        return [atacante, aliado, _unidad("R1", "rojo", "Tanque", 3, 4, 2)]
    if numero == 6:
        return [atacante, aliado, _unidad("R1", "rojo", "Infante", 2, 4, 2),
                _unidad("R2", "rojo", "Tanque", 3, 4, 2)]
    if numero == 7:
        return [atacante, _unidad("A2", "azul", "Infante", 1, 1),
                _unidad("R1", "rojo", "Infante", 3, 6, 2),
                _unidad("R2", "rojo", "Infante", 3, 3, 2),
                _unidad("R3", "rojo", "Tanque", 4, 6)]
    if numero == 8:
        return [atacante, _unidad("A2", "azul", "Infante", 1, 3),
                _unidad("R1", "rojo", "Infante", 3, 4, 2),
                _unidad("R2", "rojo", "Infante", 4, 4, 2),
                _unidad("A3", "azul", "Tanque", 3, 0),
                _unidad("R3", "rojo", "Tanque", 3, 7)]
    tipos = {1: ("Arquero", "Tanque", "Tanque"),
             2: ("Infante", "Tanque", "Tanque"),
             3: ("Arquero", "Infante", "Tanque"),
             4: ("Infante", "Arquero", "Tanque"),
             5: ("Tanque", "Infante", "Tanque")}[numero]
    if numero in (3, 4):
        aliado["tipo"] = "Arquero"
        aliado["vida_max"] = CONFIG_TIPOS["Arquero"]["vida"]
    unidades = [atacante, aliado]
    for indice, (tipo, posicion) in enumerate(zip(tipos, [(3, 4), (3, 3), (3, 5)]), 1):
        vida = None if indice == 1 and numero in (2, 5) else 2
        unidades.append(_unidad(f"R{indice}", "rojo", tipo, *posicion, vida))
    return unidades
