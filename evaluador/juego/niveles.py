"""Lecciones progresivas: encuentros de demostración, prácticas y retos independientes."""
from copy import deepcopy

from .tipos import CONFIG_TIPOS


RETO_UNIVERSAL = (
    "(Enemigo(objetivo) & forall y (Cerca(objetivo,y) -> exists z (Mio(z) & Cerca(y,z))))"
)
ORDEN_POR_VECINO = "forall y (Mio(y) -> exists z (Cerca(objetivo,z) & Alineado(y,z)))"
ORDEN_UNICO = "exists z (Cerca(objetivo,z) & forall y (Mio(y) -> Alineado(y,z)))"


def _unidad(nombre, bando, tipo, col, fila, vida=None) -> dict:
    """Construye un soldado; una vida omitida significa vida completa."""
    maxima = CONFIG_TIPOS[tipo]["vida"]
    return {"id": nombre, "bando": bando, "tipo": tipo, "col": col, "fila": fila,
            "vida": maxima if vida is None else vida, "vida_max": maxima,
            "movio": False, "ataco": False}


def _grupo(datos, atacante=(1, 4)) -> list[dict]:
    """Forma un encuentro pequeño a partir de filas legibles de soldados."""
    return [_unidad("A1", "azul", "Arquero", *atacante, 2)] + [
        _unidad(nombre, "azul" if nombre.startswith("A") else "rojo", tipo, col, fila, vida)
        for nombre, tipo, col, fila, vida in datos
    ]


def _explicacion(titulo, texto, simbolo=None, resaltar=None) -> dict:
    """Presenta una sola idea antes de pedir que el estudiante la use."""
    return {"tipo": "explicacion", "titulo": titulo, "texto": texto,
            "simbolo": simbolo, "resaltar": resaltar or []}


def _ejemplo(formula, unidades, comentar, texto, titulo="Miremos juntos") -> dict:
    """Muestra una fórmula sobre un mundo distinto del reto."""
    return {"tipo": "ejemplo", "titulo": titulo, "formula": formula,
            "unidades": unidades, "comentar": comentar, "texto": texto}


def _practica(objetivo, solucion, plantilla, unidades, idea, casi, titulo) -> dict:
    """Escalona la ayuda desde una idea hasta la respuesta de esta práctica."""
    return {"tipo": "practica", "titulo": titulo, "objetivo": objetivo,
            "solucion": solucion, "plantilla": plantilla, "unidades": unidades,
            "pistas": [idea, casi, solucion]}


def _leccion(numero, titulo, simbolos, predicados, nuevo, objetivos, solucion, pasos) -> dict:
    """Conserva el contrato y reserva la solución completa para el reto y Ver respuesta."""
    objetivo = "Golpea exactamente a " + ", ".join(objetivos) + " con A1."
    pasos = pasos + [{"tipo": "reto", "titulo": "Resuelve otro encuentro", "objetivo": objetivos,
                      "solucion": solucion, "texto": objetivo + " Usa lo que acabas de aprender."}]
    return {
        "id": numero, "titulo": titulo, "descripcion": objetivo, "objetivo": objetivo,
        "simbolos": predicados + simbolos, "simbolos_permitidos": simbolos,
        "predicados_permitidos": predicados, "simbolo_nuevo": nuevo,
        "objetivos": objetivos, "atacante": "A1", "solucion_ejemplo": solucion,
        "pista": "Prueba tu fórmula y compara las unidades que sobran y faltan.",
        "explicacion": pasos[0]["texto"], "pasos": pasos,
    }


def _inicio() -> dict:
    """Distingue el dominio, el valor de verdad y los objetivos realmente alcanzados."""
    ejemplo = _grupo([("A2", "Tanque", 1, 2, None), ("R2", "Infante", 3, 4, None),
                      ("R3", "Tanque", 8, 7, None)])
    practica = _grupo([("A3", "Infante", 2, 4, None), ("R4", "Tanque", 3, 4, None)])
    pasos = [
        _explicacion("Tu fórmula decide a quién atacar",
                     "Rojo: enemigo. Azul: aliado. objetivo nombra al soldado que revisamos. "
                     "Es una constante: puedes usarla sin cuantificador. Mio(objetivo) pregunta si es aliado."),
        _ejemplo("Mio(objetivo)", ejemplo, ["A1", "A2"],
                 "A2 es aliado: cumple la fórmula. A1 es tu atacante y no se ataca a sí mismo."),
        _explicacion("Cumplir no basta para recibir el ataque",
                     "La fórmula debe ser verdadera y el soldado debe estar en alcance. "
                     "Tu arquero llega a 4 casillas, contando filas y columnas."),
        _practica(["A3"], "Mio(objetivo)", "___(objetivo)", practica, "Busca al compañero del equipo en turno.",
                  "El predicado que pregunta por tu equipo es Mio.", "Completa el predicado"),
    ]
    return _leccion(0, "El campo de batalla", [], ["Mio", "Enemigo"], "Enemigo",
                    ["R1"], "Enemigo(objetivo)", pasos)


def _tipos() -> dict:
    """Contrasta tipo y bando antes de combinarlos en lecciones posteriores."""
    ejemplo = _grupo([("R2", "Tanque", 3, 4, None), ("A2", "Infante", 1, 2, None)])
    practica = _grupo([("R3", "Infante", 2, 4, None), ("A3", "Tanque", 1, 2, None),
                      ("R4", "Tanque", 3, 3, None)])
    pasos = [
        _explicacion("Pregunta qué tipo de soldado es",
                     "Tanque(objetivo) pregunta si es tanque. También puedes preguntar por Infante, Arquero o Medico. "
                     "El tipo y el equipo son cosas distintas."),
        _ejemplo("Tanque(objetivo)", ejemplo, ["R2", "A2"],
                 "R2 es tanque aunque sea enemigo. A2 es de tu equipo, pero es infante."),
        _practica(["R3"], "Infante(objetivo)", "___(objetivo)", practica, "Pregunta por el tipo de R3.",
                  "Escribe el nombre del tipo y después su argumento (objetivo).", "Escribe otro predicado"),
    ]
    return _leccion(1, "Predicados de tipo", [],
                    ["Arquero", "Infante", "Tanque", "Medico", "Mio", "Enemigo"],
                    "Arquero", ["R1"], "Arquero(objetivo)", pasos)


def _negacion() -> dict:
    """Define el umbral estricto de Herido y evita llamar sano a todo no herido."""
    ejemplo = _grupo([("R2", "Tanque", 3, 4, 16), ("R3", "Infante", 3, 3, 5),
                      ("A2", "Arquero", 1, 2, 2)])
    practica = _grupo([("R4", "Infante", 3, 4, 5), ("A3", "Arquero", 1, 2, 2)])
    pasos = [
        _explicacion("¿Está herido?", "Herido significa menos de media vida: 2/7 sí; 5/10 no. "
                     "No estar herido no significa tener toda la vida.",
                     resaltar=["R2", "R3", "A2"]),
        _ejemplo("Arquero(objetivo)", ejemplo, ["R3", "A2"],
                 "A2 es arquero y tiene 2/7 de vida; R3 es infante y tiene 5/10. "
                 "Solo A2 está por debajo de la mitad de su vida máxima."),
        _explicacion("Invierte la respuesta", "¬ significa no: invierte verdadero y falso. "
                     "Escríbelo con ~ o ! antes de la pregunta que quieres negar.", "¬"),
        _ejemplo("~Tanque(objetivo)", ejemplo, ["R2", "R3"],
                 "Negar Tanque selecciona infantes y arqueros, sin preguntar por su vida."),
        _practica(["R4"], "~Arquero(objetivo)", "___Arquero(objetivo)", practica,
                  "Excluye a los arqueros.", "Pon ~ delante del predicado Arquero.",
                  "Completa una negación"),
    ]
    return _leccion(2, "Negación", ["¬"], ["Herido", "Tanque", "Arquero"],
                    "¬", ["R1"], "~Herido(objetivo)", pasos)


def _conjuncion() -> dict:
    """Construye la sintaxis binaria y después cambia las dos condiciones."""
    ejemplo = _grupo([("R2", "Infante", 3, 4, 2), ("A2", "Infante", 1, 2, 2)])
    primera = _grupo([("A3", "Arquero", 2, 4, 2), ("R3", "Arquero", 3, 4, 2),
                      ("A4", "Infante", 1, 2, 2)])
    segunda = _grupo([("R4", "Tanque", 3, 4, 2), ("A4", "Tanque", 1, 2, 2),
                      ("R5", "Infante", 3, 3, 2)])
    tercera = _grupo([("A5", "Tanque", 2, 4, 2), ("R6", "Tanque", 3, 4, 2),
                      ("A6", "Infante", 1, 2, 2)])
    pasos = [
        _explicacion("Y: cumple las dos condiciones", "∧ se escribe &. Las dos condiciones deben ser verdaderas. "
                     "Une las preguntas así: (pregunta & pregunta). No olvides los paréntesis exteriores.", "∧"),
        _ejemplo("(Enemigo(objetivo) & Infante(objetivo))", ejemplo, ["R2", "A2"],
                 "Primero pregunta el bando, luego el tipo. R2 pasa ambas preguntas; A2 falla la primera."),
        _practica(["A3"], "(Mio(objetivo) & Arquero(objetivo))", "(Mio(objetivo) ___ Arquero(objetivo))", primera,
                  "Exige simultáneamente tu equipo y el tipo arquero.", "El hueco necesita &.",
                  "Completa el enlace"),
        _practica(["R4"], "(Enemigo(objetivo) & Tanque(objetivo))", "(Enemigo(objetivo) & ___)", segunda,
                  "La segunda parte debe preguntar si es tanque.", "Escribe Tanque(objetivo) en el hueco.",
                  "Escribe una condición"),
        _practica(["A5"], "(Mio(objetivo) & Tanque(objetivo))", "", tercera,
                  "Ahora selecciona solo los tanques de tu equipo.",
                  "Combina Mio(objetivo) con Tanque(objetivo) y conserva los paréntesis exteriores.",
                  "Escribe la fórmula completa"),
    ]
    return _leccion(3, "Conjunción", ["∧"], ["Enemigo", "Mio", "Arquero", "Infante", "Tanque"],
                    "∧", ["R1"], "(Enemigo(objetivo) & Arquero(objetivo))", pasos)


def _disyuncion() -> dict:
    """Pasa de una unión sencilla a combinar una unión con el bando."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("A3", "Tanque", 1, 2, 2),
                      ("R4", "Arquero", 3, 3, 2)])
    primera = _grupo([("A4", "Tanque", 1, 2, 16), ("R5", "Infante", 3, 4, 2),
                      ("R6", "Tanque", 3, 3, 16)])
    segunda = _grupo([("R7", "Arquero", 3, 4, 2), ("R8", "Tanque", 3, 3, 2),
                      ("A5", "Arquero", 1, 2, 2), ("R9", "Infante", 3, 5, 2)])
    pasos = [
        _explicacion("O: basta una condición", "∨ se escribe |. Basta cumplir una de las condiciones; "
                     "también puede cumplir ambas. Usa (pregunta | pregunta).", "∨"),
        _ejemplo("(Infante(objetivo) | Tanque(objetivo))", ejemplo, ["R3", "A3"],
                 "La unión incluye los dos tipos, sin filtrar todavía por equipo."),
        _practica(["A4", "R5"], "(Mio(objetivo) | Herido(objetivo))", "(Mio(objetivo) ___ Herido(objetivo))", primera,
                  "Selecciona a tu compañero o a quien tenga menos de media vida.",
                  "Conecta las preguntas con |.", "Completa una unión"),
        _practica(["R7", "R8"], "(Enemigo(objetivo) & (Arquero(objetivo) | Tanque(objetivo)))", "", segunda,
                  "Une arqueros y tanques y exige que sean enemigos.",
                  "La unión va dentro de una conjunción con Enemigo(objetivo).", "Escribe la fórmula completa"),
    ]
    return _leccion(4, "Disyunción", ["∧", "∨"],
                    ["Enemigo", "Mio", "Herido", "Infante", "Arquero", "Tanque"],
                    "∨", ["R1", "R2"], "(Enemigo(objetivo) & (Infante(objetivo) | Arquero(objetivo)))", pasos)


def _implicacion() -> dict:
    """Explica la condición falsa antes de aplicar una restricción táctica por tipo."""
    ejemplo = _grupo([("R3", "Tanque", 3, 4, 16), ("R4", "Tanque", 3, 3, 2),
                      ("A3", "Infante", 1, 2, 10), ("R5", "Infante", 3, 5, 2)])
    primera = _grupo([("R5", "Arquero", 3, 4, 2), ("A4", "Infante", 1, 2, 10),
                      ("R6", "Arquero", 3, 3, 7)])
    segunda = _grupo([("R7", "Arquero", 3, 4, 2), ("R8", "Tanque", 3, 3, 16),
                      ("A5", "Infante", 1, 2, 10), ("R9", "Arquero", 3, 5, 7)])
    tabla = [{"antecedente": a, "consecuente": b, "resultado": not a or b}
             for a, b in [(False, False), (False, True), (True, False), (True, True)]]
    explicacion = _explicacion(
        "Si… entonces…", "→ se escribe ->. Solo es falso cuando la primera condición es verdadera "
        "y la segunda es falsa. Si la primera es falsa, la regla es verdadera.", "→")
    explicacion["tabla_verdad"] = tabla
    pasos = [
        explicacion,
        _ejemplo("(Herido(objetivo) -> Tanque(objetivo))", ejemplo, ["R4", "R5"],
                 "Si tiene menos de media vida, exige que sea tanque: R4 cumple y R5 no. "
                 "Para R3 y A3 la condición inicial es falsa, así que la implicación es verdadera."),
        _practica(["A4", "R5"], "(Arquero(objetivo) -> Herido(objetivo))",
                  "(Arquero(objetivo) ___ Herido(objetivo))", primera, "Restringe ahora a los arqueros.",
                  "Usa ->: si es arquero debe estar herido.", "Completa la condición"),
        _practica(["R7", "R8"], "(Enemigo(objetivo) & (Arquero(objetivo) -> Herido(objetivo)))", "", segunda,
                  "Conserva la restricción para arqueros y evita fuego amigo.",
                  "Exige Enemigo(objetivo) y además la implicación.", "Añade el filtro de bando"),
    ]
    nivel = _leccion(5, "Implicación", ["∧", "→"], ["Enemigo", "Tanque", "Arquero", "Herido"],
                     "→", ["R1", "R2"], "(Enemigo(objetivo) & (Tanque(objetivo) -> Herido(objetivo)))", pasos)
    nivel["tabla_verdad"] = tabla
    return nivel


def _relaciones() -> dict:
    """Introduce dos argumentos y la constante relativa al atacante."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("A3", "Tanque", 1, 2, 2),
                      ("R4", "Tanque", 3, 3, 2)])
    practica = _grupo([("R5", "Infante", 1, 1, 2), ("A4", "Tanque", 2, 4, 2),
                      ("R6", "Tanque", 3, 3, 2)])
    pasos = [
        _explicacion("Compara dos soldados", "yo nombra a tu atacante. Cerca pregunta "
                     "si dos soldados están a una casilla. Alineado pregunta si comparten fila o columna. "
                     "No se compara un soldado consigo mismo."),
        _ejemplo("Alineado(objetivo,yo)", ejemplo, ["R3", "R4"],
                 "R3 comparte fila con el atacante; R4 no comparte ni fila ni columna."),
        _practica(["A4"], "Cerca(yo,objetivo)", "Cerca(___,objetivo)", practica,
                  "Selecciona a quien esté a una casilla del atacante, no solo en su fila o columna.",
                  "La constante que representa al atacante es yo.", "Completa el otro argumento"),
    ]
    return _leccion(6, "Relaciones y yo", [], ["Cerca", "Alineado", "yo"],
                    "Cerca", ["R1"], "Cerca(objetivo,yo)", pasos)


def _existencial() -> dict:
    """Busca un testigo, filtra su bando y finalmente niega que exista."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("R4", "Tanque", 3, 5, 2),
                      ("A3", "Tanque", 1, 1, 2)])
    primera = _grupo([("R5", "Infante", 3, 4, 2), ("A4", "Tanque", 3, 5, 2),
                      ("R6", "Tanque", 1, 1, 2)])
    segunda = _grupo([("R7", "Infante", 3, 4, 2), ("A5", "Tanque", 3, 5, 2),
                      ("A6", "Infante", 1, 3, 2), ("R8", "Tanque", 4, 4, 2)])
    pasos = [
        _explicacion("Existe: encuentra al menos uno", "∃ se escribe exists. Busca un soldado y que cumpla la condición: "
                     "ese es el testigo. Escribe exists y para que y quede ligada, sin variables libres.", "∃"),
        _ejemplo("exists y Cerca(objetivo,y)", ejemplo, ["R3", "A3"],
                 "R4 sirve de testigo para R3. A3 no tiene vecino: nadie sirve de testigo."),
        _practica(["R5"], "exists y (Mio(y) & Cerca(objetivo,y))",
                  "exists y (___ & Cerca(objetivo,y))", primera,
                  "El vecino debe ser de nuestro equipo, aunque objetivo pueda ser enemigo.",
                  "Exige Mio(y), porque y es el vecino que buscas.", "Escribe la condición del testigo"),
        _practica(["R7"], "(Enemigo(objetivo) & exists y (Mio(y) & Cerca(objetivo,y)))", "", segunda,
                  "Distingue el bando de la constante objetivo del bando del testigo y.",
                  "Exige Enemigo(objetivo) por fuera y Mio(y) dentro de exists.", "Selecciona enemigos acompañados"),
        _explicacion("Que no exista ninguno", "Negar exists significa que no hay ningún soldado que cumpla la condición. "
                     "La cercanía no causa daño: solo sirve para elegir objetivos."),
    ]
    return _leccion(7, "Existe", ["∧", "¬", "∃"], ["Enemigo", "Mio", "Cerca"],
                    "∃", ["R1"], "(Enemigo(objetivo) & ~exists y (Mio(y) & Cerca(objetivo,y)))", pasos)


def _vigilancia(espejo=False) -> list[dict]:
    """Coloca el encuentro verificado con dos vigilantes distintos y un vecino descubierto."""
    unidades = _grupo([
        ("R1", "Infante", 4, 4, 2), ("R2", "Infante", 3, 4, 2),
        ("R3", "Infante", 5, 4, 2), ("A2", "Tanque", 3, 3, 16),
        ("A3", "Tanque", 5, 3, 16), ("R4", "Infante", 2, 3, 2),
        ("R5", "Infante", 1, 3, 2),
    ], atacante=(4, 1))
    if espejo:
        for unidad in unidades:
            unidad["col"] = 9 - unidad["col"]
            if unidad["id"].startswith("R"):
                unidad["id"] = "R" + str(int(unidad["id"][1:]) + 5)
    return unidades


def _alineacion_guiada() -> list[dict]:
    """Separa dos puntos próximos a R6, cada uno alineado con un aliado diferente."""
    return _grupo([
        ("A2", "Tanque", 3, 2, 16), ("R6", "Infante", 3, 4, 2),
        ("R7", "Infante", 3, 3, 2), ("R8", "Infante", 4, 4, 2),
        ("R9", "Infante", 2, 2, 2),
    ])


def _universal() -> dict:
    """Separa comprobación universal, contraejemplo y orden de testigos."""
    ejemplo = _grupo([("A2", "Tanque", 3, 4, 16), ("R3", "Infante", 2, 4, 2),
                      ("R4", "Infante", 4, 4, 2)])
    primera = _grupo([("A3", "Tanque", 2, 3, 16), ("R5", "Infante", 1, 3, 2),
                      ("R6", "Infante", 3, 3, 2)])
    segunda = _grupo([("A4", "Tanque", 3, 5, 16), ("R7", "Infante", 3, 4, 2),
                      ("R8", "Infante", 4, 5, 2), ("R9", "Infante", 5, 5, 2),
                      ("R10", "Infante", 3, 1, 2), ("A5", "Infante", 1, 3, 10)])
    pasos = [
        _explicacion("Para todos: no puede fallar ninguno", "∀ se escribe forall. Todos los soldados deben cumplir la condición. "
                     "Si uno falla, la fórmula es falsa: ese soldado es el contraejemplo.", "∀"),
        _ejemplo("forall y (Mio(y) -> Cerca(objetivo,y))", ejemplo, ["R3", "R4"],
                 "Para R3, todos nuestros aliados están cerca. Para R4, A1 está lejos: "
                 "A1 es el contraejemplo. Mira su nombre en la explicación.", "Encuentra el contraejemplo"),
        _practica(["R5"], "(Enemigo(objetivo) & forall y (Mio(y) -> Cerca(objetivo,y)))",
                  "(Enemigo(objetivo) & ___ y (Mio(y) -> Cerca(objetivo,y)))", primera,
                  "Exige cercanía a cada aliado, no solo a alguno.",
                  "El hueco necesita forall.", "Completa el universal"),
        _practica(["R7"], "(Enemigo(objetivo) & forall y (Cerca(objetivo,y) -> Mio(y)))", "", segunda,
                  "Ataca enemigos cuyos vecinos sean todos de nuestro equipo.",
                  "La condición inicial es Cerca(objetivo,y); lo exigido es Mio(y).",
                  "Cambia qué condición exiges a todos"),
        _explicacion("Un punto de alineación para cada aliado",
                     "forall y exists z permite un z distinto para cada y. "
                     "exists z forall y exige el mismo z para todos. Mira cómo cambia el resultado."),
        _ejemplo(ORDEN_POR_VECINO, _alineacion_guiada(), ["R6", "R9"],
                 "Cerca de R6, R7 está alineado con A2 y R8 con A1: cada aliado tiene su punto. "
                 "R6 no puede usarse como su propio punto cercano porque Cerca excluye al mismo soldado.",
                 "Para cada aliado, algún punto alineado"),
        _ejemplo(ORDEN_UNICO, _alineacion_guiada(), ["R6", "R9"],
                 "Ningún soldado cercano a R6 está alineado con A1 y A2 a la vez. "
                 "El costo es el mismo, pero R6 ya no cumple la fórmula.",
                 "Un mismo punto alineado con todos"),
    ]
    return _leccion(8, "Para todo y anidación", ["∧", "→", "∃", "∀"],
                    ["Enemigo", "Mio", "Cerca", "Alineado"],
                    "∀", ["R1"], RETO_UNIVERSAL, pasos)


_NIVELES = [_inicio(), _tipos(), _negacion(), _conjuncion(), _disyuncion(),
            _implicacion(), _relaciones(), _existencial(), _universal()]


def datos_nivel(numero: int) -> dict:
    """Devuelve metadatos independientes sin calcular estados ni lecturas."""
    return deepcopy(_NIVELES[numero])


def niveles() -> list[dict]:
    """Añade a cada paso su estado reproducible y a cada ejemplo su lectura en español."""
    from .formulas import _evaluar_objetivos
    from .lectura import leer_formula
    from .partida import crear_estado

    salida = deepcopy(_NIVELES)
    for nivel in salida:
        for indice, paso in enumerate(nivel["pasos"]):
            paso["estado"] = crear_estado("tutorial", nivel=nivel["id"], paso=indice)
            if paso["tipo"] == "ejemplo":
                paso["lectura"] = leer_formula(paso["formula"])
                estado = paso["estado"]
                _, _, _, afectados = _evaluar_objetivos(estado, estado["unidades"][0], paso["formula"])
                paso["objetivo"] = sorted(o["id"] for o in afectados)
    return salida


def _unidades_nivel(numero: int, paso=None) -> list[dict]:
    """Selecciona el encuentro del paso o el reto cuando no se indica paso."""
    if paso is not None:
        datos = _NIVELES[numero]["pasos"][paso]
        if "unidades" in datos:
            return deepcopy(datos["unidades"])
        # Una explicación usa el siguiente encuentro guiado, nunca adelanta la solución del reto.
        if datos["tipo"] == "explicacion":
            for siguiente in _NIVELES[numero]["pasos"][paso + 1:]:
                if "unidades" in siguiente:
                    return deepcopy(siguiente["unidades"])
    if numero == 8:
        return _vigilancia()
    if numero == 7:
        return _grupo([("R1", "Infante", 3, 6, 2), ("R2", "Infante", 3, 3, 2),
                       ("A2", "Tanque", 3, 2, 16)])
    if numero == 5:
        return _grupo([("R1", "Infante", 3, 4, 10), ("R2", "Tanque", 3, 3, 2),
                       ("R3", "Tanque", 3, 5, 16), ("A2", "Infante", 1, 2, 10)])
    if numero == 0:
        return _grupo([("R1", "Tanque", 3, 4, 2), ("A2", "Infante", 1, 2, 10),
                       ("R2", "Infante", 8, 7, 10)])
    if numero == 6:
        return _grupo([("R1", "Infante", 2, 4, 2), ("R2", "Tanque", 3, 4, 2),
                       ("A2", "Tanque", 1, 2, 2)])
    tipos = {1: ("Arquero", "Tanque", "Infante"), 2: ("Infante", "Tanque", "Tanque"),
             3: ("Arquero", "Infante", "Tanque"), 4: ("Infante", "Arquero", "Tanque")}[numero]
    aliado = "Arquero" if numero in (3, 4) else "Tanque"
    unidades = _grupo([("A2", aliado, 1, 2, 2)])
    for indice, (tipo, posicion) in enumerate(zip(tipos, [(3, 4), (3, 3), (3, 5)]), 1):
        vida = 5 if numero == 2 and indice == 1 else 2
        unidades.append(_unidad(f"R{indice}", "rojo", tipo, *posicion, vida))
    return unidades
