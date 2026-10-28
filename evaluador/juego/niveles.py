"""Lecciones progresivas: encuentros de demostración, prácticas y retos independientes."""
from copy import deepcopy

from .tipos import CONFIG_TIPOS


RETO_UNIVERSAL = (
    "(Enemigo(x) & forall y (Cerca(x,y) -> exists z (Mio(z) & Cerca(y,z))))"
)
ORDEN_POR_VECINO = "forall y (Cerca(x,y) -> exists z (Mio(z) & Cerca(y,z)))"
ORDEN_UNICO = "exists z (Mio(z) & forall y (Cerca(x,y) -> Cerca(y,z)))"


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
        _explicacion("El mundo y x", "Cada soldado vivo pertenece al dominio: la lista que revisa el juego. "
                     "x significa el soldado que estamos revisando, uno por uno. "
                     "Mio pregunta si es del equipo que tiene el turno; Enemigo, si es del otro equipo. "
                     "Al cambiar el turno, estas respuestas se invierten."),
        _ejemplo("Mio(x)", ejemplo, ["A1", "A2"],
                 "Mio(x) es verdadero para A1 y A2, pero A1 no se golpea a sí mismo. "
                 "Los paréntesis de Mio(x) contienen su argumento: el soldado x."),
        _explicacion("Cumplir no basta para recibir el ataque",
                     "Una unidad cumple la fórmula cuando la respuesta es verdadera. "
                     "Solo recibe el ataque si además está en alcance y no es el atacante. "
                     "Un arquero alcanza hasta cuatro casillas de distancia, contando filas y columnas. "
                     "En el reto habrá un enemigo dentro del alcance y otro fuera."),
        _practica(["A3"], "Mio(x)", "___(x)", practica, "Busca al compañero del equipo en turno.",
                  "El predicado que pregunta por tu equipo es Mio.", "Completa el predicado"),
    ]
    return _leccion(0, "El campo de batalla", [], ["Mio", "Enemigo"], "Enemigo",
                    ["R1"], "Enemigo(x)", pasos)


def _tipos() -> dict:
    """Contrasta tipo y bando antes de combinarlos en lecciones posteriores."""
    ejemplo = _grupo([("R2", "Tanque", 3, 4, None), ("A2", "Infante", 1, 2, None)])
    practica = _grupo([("R3", "Infante", 2, 4, None), ("A3", "Tanque", 1, 2, None)])
    pasos = [
        _explicacion("Preguntas sobre el tipo", "Un predicado es una pregunta sobre un soldado. "
                     "Infante(x) pregunta si x es infante; Arquero pregunta si es arquero; "
                     "Tanque(x), si es tanque; Medico(x), si es médico. El tipo no indica el bando. "
                     "Mio y Enemigo se refieren al equipo que tiene el turno, no al color para siempre."),
        _ejemplo("Tanque(x)", ejemplo, ["R2", "A2"],
                 "R2 es tanque aunque sea enemigo. A2 es de tu equipo, pero es infante."),
        _practica(["R3"], "Infante(x)", "___(x)", practica, "Pregunta por el tipo de R3.",
                  "Escribe el nombre del tipo y después su argumento (x).", "Escribe otro predicado"),
    ]
    return _leccion(1, "Predicados de tipo", [],
                    ["Arquero", "Infante", "Tanque", "Mio", "Enemigo"],
                    "Arquero", ["R1"], "Arquero(x)", pasos)


def _negacion() -> dict:
    """Define el umbral estricto de Herido y evita llamar sano a todo no herido."""
    ejemplo = _grupo([("R2", "Tanque", 3, 4, 16), ("R3", "Infante", 3, 3, 5),
                      ("A2", "Arquero", 1, 2, 2)])
    practica = _grupo([("R4", "Infante", 3, 4, 5), ("A3", "Arquero", 1, 2, 2)])
    pasos = [
        _explicacion("Herido y no herido", "Herido significa menos de la mitad de la vida máxima. "
                     "16/16 no cumple; 5/10 tampoco cumple, porque es exactamente la mitad; "
                     "2/7 sí cumple. No herido puede haber perdido vida: no significa vida completa.",
                     resaltar=["R2", "R3", "A2"]),
        _ejemplo("Herido(x)", ejemplo, ["R3", "A2"],
                 "Compara 5/10 con 2/7: solo el segundo está por debajo de la mitad."),
        _explicacion("Invierte la respuesta", "¬ significa no: invierte verdadero y falso. "
                     "Escríbelo con ~ o ! antes de la pregunta que quieres negar.", "¬"),
        _ejemplo("~Tanque(x)", ejemplo, ["R2", "R3"],
                 "Negar Tanque selecciona infantes y arqueros, sin preguntar por su vida."),
        _practica(["R4"], "~Arquero(x)", "___Arquero(x)", practica,
                  "Excluye a los arqueros.", "Pon ~ delante del predicado Arquero.",
                  "Completa una negación"),
    ]
    return _leccion(2, "Negación", ["¬"], ["Herido", "Tanque", "Arquero"],
                    "¬", ["R1"], "~Herido(x)", pasos)


def _conjuncion() -> dict:
    """Construye la sintaxis binaria y después cambia las dos condiciones."""
    ejemplo = _grupo([("R2", "Infante", 3, 4, 2), ("A2", "Infante", 1, 2, 2)])
    primera = _grupo([("A3", "Arquero", 2, 4, 2), ("R3", "Arquero", 3, 4, 2)])
    segunda = _grupo([("R4", "Tanque", 3, 4, 2), ("A4", "Tanque", 1, 2, 2),
                      ("R5", "Infante", 3, 3, 2)])
    tercera = _grupo([("A5", "Tanque", 2, 4, 2), ("R6", "Tanque", 3, 4, 2),
                      ("A6", "Infante", 1, 2, 2)])
    pasos = [
        _explicacion("Dos condiciones a la vez", "∧ significa y: ambas respuestas deben ser verdaderas. "
                     "Escribe &. Los paréntesis de cada predicado contienen su argumento, como (x). "
                     "Además, toda fórmula con dos partes lleva paréntesis por fuera: "
                     "(pregunta izquierda & pregunta derecha). No omitas esos paréntesis.", "∧"),
        _ejemplo("(Enemigo(x) & Infante(x))", ejemplo, ["R2", "A2"],
                 "Primero pregunta el bando, luego el tipo. R2 pasa ambas preguntas; A2 falla la primera."),
        _practica(["A3"], "(Mio(x) & Arquero(x))", "(Mio(x) ___ Arquero(x))", primera,
                  "Exige simultáneamente tu equipo y el tipo arquero.", "El hueco necesita &.",
                  "Completa el enlace"),
        _practica(["R4"], "(Enemigo(x) & Tanque(x))", "(Enemigo(x) & ___)", segunda,
                  "La segunda parte debe preguntar si es tanque.", "Escribe Tanque(x) en el hueco.",
                  "Escribe una condición"),
        _practica(["A5"], "(Mio(x) & Tanque(x))", "", tercera,
                  "Ahora selecciona solo los tanques de tu equipo.",
                  "Combina Mio(x) con Tanque(x) y conserva los paréntesis exteriores.",
                  "Escribe la fórmula completa"),
    ]
    return _leccion(3, "Conjunción", ["∧"], ["Enemigo", "Mio", "Arquero", "Infante", "Tanque"],
                    "∧", ["R1"], "(Enemigo(x) & Arquero(x))", pasos)


def _disyuncion() -> dict:
    """Pasa de una unión sencilla a combinar una unión con el bando."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("A3", "Tanque", 1, 2, 2),
                      ("R4", "Arquero", 3, 3, 2)])
    primera = _grupo([("A4", "Tanque", 1, 2, 16), ("R5", "Infante", 3, 4, 2),
                      ("R6", "Tanque", 3, 3, 16)])
    segunda = _grupo([("R7", "Arquero", 3, 4, 2), ("R8", "Tanque", 3, 3, 2),
                      ("A5", "Arquero", 1, 2, 2), ("R9", "Infante", 3, 5, 2)])
    pasos = [
        _explicacion("Una condición u otra", "∨ significa o: basta con una respuesta verdadera; "
                     "si ambas lo son también sirve. Escribe |. Mantén los paréntesis exteriores. "
                     "Cuando combinas fórmulas, cada pareja conserva sus propios paréntesis.", "∨"),
        _ejemplo("(Infante(x) | Tanque(x))", ejemplo, ["R3", "A3"],
                 "La unión incluye los dos tipos, sin filtrar todavía por equipo."),
        _practica(["A4", "R5"], "(Mio(x) | Herido(x))", "(Mio(x) ___ Herido(x))", primera,
                  "Selecciona a tu compañero o a quien tenga menos de media vida.",
                  "Conecta las preguntas con |.", "Completa una unión"),
        _practica(["R7", "R8"], "(Enemigo(x) & (Arquero(x) | Tanque(x)))", "", segunda,
                  "Une arqueros y tanques y exige que sean enemigos.",
                  "La unión va dentro de una conjunción con Enemigo(x).", "Escribe la fórmula completa"),
    ]
    return _leccion(4, "Disyunción", ["∧", "∨"],
                    ["Enemigo", "Mio", "Herido", "Infante", "Arquero", "Tanque"],
                    "∨", ["R1", "R2"], "(Enemigo(x) & (Infante(x) | Arquero(x)))", pasos)


def _implicacion() -> dict:
    """Explica la condición falsa antes de aplicar una restricción táctica por tipo."""
    ejemplo = _grupo([("R3", "Tanque", 3, 4, 16), ("R4", "Tanque", 3, 3, 2),
                      ("A3", "Infante", 1, 2, 10)])
    primera = _grupo([("R5", "Arquero", 3, 4, 2), ("A4", "Infante", 1, 2, 10),
                      ("R6", "Arquero", 3, 3, 7)])
    segunda = _grupo([("R7", "Arquero", 3, 4, 2), ("R8", "Tanque", 3, 3, 16),
                      ("A5", "Infante", 1, 2, 10), ("R9", "Arquero", 3, 5, 7)])
    tabla = [{"antecedente": a, "consecuente": b, "resultado": not a or b}
             for a, b in [(False, False), (False, True), (True, False), (True, True)]]
    explicacion = _explicacion(
        "Si se cumple una condición", "→ se escribe ->. La primera parte se llama antecedente: "
        "la condición inicial. La segunda es lo que exigimos cuando esa condición es verdadera. "
        "Solo falla si la condición es verdadera y lo exigido es falso. "
        "Si la condición inicial es falsa, la implicación es verdadera.", "→")
    explicacion["tabla_verdad"] = tabla
    pasos = [
        explicacion,
        _ejemplo("(Tanque(x) -> Herido(x))", ejemplo, ["R3", "A3"],
                 "Exige menos de media vida solo a los tanques. A3 no es tanque: "
                 "la condición inicial es falsa y la implicación es verdadera, aunque A3 sea aliado."),
        _practica(["A4", "R5"], "(Arquero(x) -> Herido(x))",
                  "(Arquero(x) ___ Herido(x))", primera, "Restringe ahora a los arqueros.",
                  "Usa ->: si es arquero debe estar herido.", "Completa la condición"),
        _practica(["R7", "R8"], "(Enemigo(x) & (Arquero(x) -> Herido(x)))", "", segunda,
                  "Conserva la restricción para arqueros y evita fuego amigo.",
                  "Exige Enemigo(x) y además la implicación.", "Añade el filtro de bando"),
    ]
    nivel = _leccion(5, "Implicación", ["∧", "→"], ["Enemigo", "Tanque", "Arquero", "Herido"],
                     "→", ["R1", "R2"], "(Enemigo(x) & (Tanque(x) -> Herido(x)))", pasos)
    nivel["tabla_verdad"] = tabla
    return nivel


def _relaciones() -> dict:
    """Introduce dos argumentos y la constante relativa al atacante."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("A3", "Tanque", 1, 2, 2),
                      ("R4", "Tanque", 3, 3, 2)])
    practica = _grupo([("R5", "Infante", 1, 1, 2), ("A4", "Tanque", 2, 4, 2),
                      ("R6", "Tanque", 3, 3, 2)])
    pasos = [
        _explicacion("Compara dos soldados", "Una relación es una pregunta sobre dos soldados. "
                     "Sus dos argumentos van dentro de los paréntesis, separados por coma. "
                     "yo es una constante: nombra siempre al atacante seleccionado. "
                     "Alineado exige misma fila o columna. Cerca exige una casilla de distancia. "
                     "Ambas excluyen comparar un soldado consigo mismo."),
        _ejemplo("Alineado(x,yo)", ejemplo, ["R3", "R4"],
                 "R3 comparte fila con el atacante; R4 no comparte ni fila ni columna."),
        _practica(["A4", "R5"], "Alineado(yo,x)", "Alineado(___,x)", practica,
                  "Compara el atacante con cada soldado x.",
                  "La constante que representa al atacante es yo.", "Completa el otro argumento"),
    ]
    return _leccion(6, "Relaciones y yo", [], ["Cerca", "Alineado", "yo"],
                    "Cerca", ["R1"], "Cerca(x,yo)", pasos)


def _existencial() -> dict:
    """Busca un testigo, filtra su bando y finalmente niega que exista."""
    ejemplo = _grupo([("R3", "Infante", 3, 4, 2), ("R4", "Tanque", 3, 5, 2),
                      ("A3", "Tanque", 1, 1, 2)])
    primera = _grupo([("R5", "Infante", 3, 4, 2), ("A4", "Tanque", 3, 5, 2),
                      ("R6", "Tanque", 1, 1, 2)])
    segunda = _grupo([("R7", "Infante", 3, 4, 2), ("A5", "Tanque", 3, 5, 2),
                      ("A6", "Infante", 1, 3, 2), ("R8", "Tanque", 4, 6, 2)])
    pasos = [
        _explicacion("Prueba cada posible vecino", "∃ se escribe exists. x sigue siendo el soldado "
                     "que revisamos; y recorre el mismo dominio: todos los soldados vivos de ambos equipos. "
                     "Un testigo es un soldado y que hace verdadera la condición. Basta encontrar uno. "
                     "Cerca(x,y) nunca acepta y igual a x.", "∃"),
        _ejemplo("exists y Cerca(x,y)", ejemplo, ["R3", "A3"],
                 "R4 sirve de testigo para R3. A3 no tiene vecino: nadie sirve de testigo."),
        _practica(["R5"], "exists y (Mio(y) & Cerca(x,y))",
                  "exists y (___ & Cerca(x,y))", primera,
                  "El vecino debe ser de nuestro equipo, aunque x pueda ser enemigo.",
                  "Exige Mio(y), porque y es el vecino que buscas.", "Escribe la condición del testigo"),
        _practica(["R7"], "(Enemigo(x) & exists y (Mio(y) & Cerca(x,y)))", "", segunda,
                  "Distingue el bando del objetivo x del bando del testigo y.",
                  "Exige Enemigo(x) por fuera y Mio(y) dentro de exists.", "Selecciona enemigos protegidos"),
        _explicacion("Que no exista ninguno", "Negar una existencia exige que ningún soldado sirva "
                     "de testigo. En el reto atacarás enemigos sin compañeros nuestros cerca; "
                     "así evitas poner en riesgo a esos compañeros."),
    ]
    return _leccion(7, "Existe", ["∧", "¬", "∃"], ["Enemigo", "Mio", "Cerca"],
                    "∃", ["R1"], "(Enemigo(x) & ~exists y (Mio(y) & Cerca(x,y)))", pasos)


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


def _universal() -> dict:
    """Separa comprobación universal, contraejemplo y orden de testigos."""
    ejemplo = _grupo([("A2", "Tanque", 3, 4, 16), ("R3", "Infante", 2, 4, 2),
                      ("R4", "Infante", 4, 4, 2)])
    primera = _grupo([("A3", "Tanque", 2, 3, 16), ("R5", "Infante", 1, 3, 2),
                      ("R6", "Infante", 3, 3, 2)])
    segunda = _grupo([("A4", "Tanque", 3, 5, 16), ("R7", "Infante", 3, 4, 2),
                      ("R8", "Infante", 4, 5, 2), ("R9", "Infante", 5, 5, 2)])
    pasos = [
        _explicacion("Debe servir para todos", "∀ se escribe forall. Para cada soldado y del dominio "
                     "comprobamos la condición. Un contraejemplo es un solo soldado que la hace falsa: "
                     "con uno basta para que falle el para todos.", "∀"),
        _ejemplo("forall y (Mio(y) -> Cerca(x,y))", ejemplo, ["R3", "R4"],
                 "Para R3, todos nuestros aliados están cerca. Para R4, A1 está lejos: "
                 "A1 es el contraejemplo. Mira su nombre en la explicación.", "Encuentra el contraejemplo"),
        _practica(["R5"], "(Enemigo(x) & forall y (Mio(y) -> Cerca(x,y)))",
                  "(Enemigo(x) & ___ y (Mio(y) -> Cerca(x,y)))", primera,
                  "Exige cercanía a cada aliado, no solo a alguno.",
                  "El hueco necesita forall.", "Completa el universal"),
        _practica(["R7"], "(Enemigo(x) & forall y (Cerca(x,y) -> Mio(y)))", "", segunda,
                  "Ataca enemigos cuyos vecinos sean todos de nuestro equipo.",
                  "La condición inicial es Cerca(x,y); lo exigido es Mio(y).",
                  "Cambia qué condición exiges a todos"),
        _explicacion("Un vigilante para cada vecino", "Ahora anidamos: colocamos un cuantificador "
                     "dentro de otro. Para cada vecino y buscamos algún aliado z cerca de y. "
                     "El vigilante z puede cambiar con y. Si buscamos z primero, el mismo aliado "
                     "tiene que servir para todos los vecinos. Compara ambos órdenes en el mismo tablero."),
        _ejemplo(ORDEN_POR_VECINO, _vigilancia(True), ["R6", "R9"],
                 "Cada vecino de R6 tiene un vigilante; pueden ser aliados distintos. "
                 "La relación Cerca impide que un soldado se vigile a sí mismo.",
                 "Para cada vecino, algún vigilante"),
        _ejemplo(ORDEN_UNICO, _vigilancia(True), ["R6", "R9"],
                 "Ahora un solo aliado tendría que vigilar a todos los vecinos de R6, "
                 "y ninguno lo logra. El costo es el mismo, pero el resultado cambia.",
                 "Un mismo vigilante para todos"),
    ]
    return _leccion(8, "Para todo y anidación", ["∧", "→", "∃", "∀"], ["Enemigo", "Mio", "Cerca"],
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
