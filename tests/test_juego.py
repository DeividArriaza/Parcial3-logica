"""Pruebas de reglas, enseñanza por búsqueda exhaustiva y entradas HTTP adversas."""
from copy import deepcopy
from itertools import product
import json
from time import perf_counter
import unittest
from unittest.mock import patch

from app import app
from evaluador.errores import ErrorValidacion
from evaluador.juego import (
    CONFIG_TIPOS, atacar, crear_estado, leer_formula, mover, niveles,
    practicar, previsualizar, terminar_turno,
)
from evaluador.juego.formulas import analizar_formula
from evaluador.juego.niveles import ORDEN_POR_VECINO, ORDEN_UNICO, RETO_UNIVERSAL
from evaluador.juego.mundo import _interpretacion
from evaluador.juego.reglas import posiciones_alcanzables
from evaluador.juego.tipos import LENGUAJE
from evaluador.juego.validacion import _validar_estado_completo
from evaluador.semantica import Evaluador
from evaluador.sintaxis import analizar


def unidad(nombre, bando, tipo, col, fila, vida=None):
    """Construye soldados de prueba con sus parámetros de vida reales."""
    maxima = CONFIG_TIPOS[tipo]["vida"]
    return {"id": nombre, "bando": bando, "tipo": tipo, "col": col, "fila": fila,
            "vida": maxima if vida is None else vida, "vida_max": maxima, "movio": False, "ataco": False}


def encuentro(unidades, turno="azul", modo="local", dificultad="facil"):
    """Prepara un encuentro válido sobre terreno transitable explícito."""
    estado = crear_estado(modo, {"azul": dificultad, "rojo": dificultad}, semilla=17)
    estado["unidades"], estado["turno"] = unidades, turno
    for soldado in unidades:
        estado["mapa"]["terreno"][soldado["fila"]][soldado["col"]] = "pasto"
    return estado


def golpea(estado, formula):
    """Consulta el conjunto exacto usando el mismo evaluador que los ataques."""
    return {o["id"] for o in previsualizar(estado, "A1", formula)["objetivos"] if o["afectado"]}


class BusquedaFormulas:
    """Enumera toda fórmula acotada, compartiendo equivalentes por tabla y variables libres."""

    def __init__(self, estado, vocabulario, omitido, variables=("x", "y")):
        """Fija el mundo y representa cada tabla de verdad mediante bits de asignaciones."""
        self.estado = estado
        self.variables = variables
        self.dominio = [u["id"] for u in estado["unidades"]]
        self.asignaciones = list(product(self.dominio, repeat=len(variables)))
        self.indice = {asignacion: i for i, asignacion in enumerate(self.asignaciones)}
        self.universo = (1 << len(self.asignaciones)) - 1
        self.operadores = set(vocabulario["simbolos_permitidos"]) - {omitido}
        self.predicados = set(vocabulario["predicados_permitidos"]) - {omitido}
        self.evaluador = Evaluador(_interpretacion(estado, "azul", "A1"))
        self.proyecciones = {
            variable: self._grupos(variable) for variable in variables
        }

    def _grupos(self, variable):
        """Agrupa asignaciones que solo difieren en la variable que se cuantifica."""
        grupos = {}
        posicion = self.variables.index(variable)
        for indice, asignacion in enumerate(self.asignaciones):
            clave = asignacion[:posicion] + asignacion[posicion + 1:]
            grupos[clave] = grupos.get(clave, 0) | (1 << indice)
        return list(grupos.values())

    def _atomos(self):
        """Genera todos los predicados con toda combinación de variables y constantes permitidas."""
        terminos = list(self.variables) + (["yo"] if "yo" in self.predicados else [])
        atomos = {}
        for nombre in sorted(self.predicados - {"yo"}):
            for argumentos in product(terminos, repeat=LENGUAJE.predicados[nombre]):
                texto = nombre + "(" + ",".join(argumentos) + ")"
                ast = analizar(texto, LENGUAJE)
                tabla = 0
                for indice, valores in enumerate(self.asignaciones):
                    entorno = dict(zip(self.variables, valores))
                    if self.evaluador.evaluar(ast, entorno).valor:
                        tabla |= 1 << indice
                libres = frozenset(a for a in argumentos if a in self.variables)
                atomos.setdefault((tabla, libres), texto)
        return atomos

    def _cuantificar(self, tabla, variable, simbolo):
        """Aplica existe o para todo sobre cada grupo de asignaciones."""
        resultado = 0
        for grupo in self.proyecciones[variable]:
            cumple = bool(tabla & grupo) if simbolo == "∃" else tabla & grupo == grupo
            if cumple:
                resultado |= grupo
        return resultado

    def generar(self, limite=3):
        """Genera todas las tablas hasta tres operadores, sin perder fórmulas distinguibles."""
        tamanos = [self._atomos()]
        vistos = set(tamanos[0])
        for tamano in range(1, limite + 1):
            nuevas = {}
            for (tabla, libres), texto in tamanos[tamano - 1].items():
                if "¬" in self.operadores:
                    nuevas.setdefault((self.universo ^ tabla, libres), "~" + texto)
                for simbolo in self.operadores & {"∃", "∀"}:
                    for variable in self.variables:
                        clave = (self._cuantificar(tabla, variable, simbolo), libres - {variable})
                        nuevas.setdefault(clave, f"{simbolo}{variable} {texto}")
            for izquierda in range(tamano):
                derecha = tamano - 1 - izquierda
                for (a, libres_a), texto_a in tamanos[izquierda].items():
                    for (b, libres_b), texto_b in tamanos[derecha].items():
                        for simbolo in self.operadores & {"∧", "∨", "→"}:
                            tabla = {"∧": a & b, "∨": a | b,
                                     "→": (self.universo ^ a) | b}[simbolo]
                            clave = tabla, libres_a | libres_b
                            nuevas.setdefault(clave, f"({texto_a} {simbolo} {texto_b})")
            nuevas = {clave: texto for clave, texto in nuevas.items() if clave not in vistos}
            vistos.update(nuevas)
            tamanos.append(nuevas)
        return {clave: texto for grupo in tamanos for clave, texto in grupo.items()}

    def seleccion(self, tabla):
        """Proyecta una fórmula con únicamente x libre sobre las unidades en alcance."""
        atacante = next(u for u in self.estado["unidades"] if u["id"] == "A1")
        resultado = set()
        for unidad in self.estado["unidades"]:
            distancia = abs(unidad["col"] - atacante["col"]) + abs(unidad["fila"] - atacante["fila"])
            asignacion = (unidad["id"],) + (self.dominio[0],) * (len(self.variables) - 1)
            if unidad["id"] != "A1" and distancia <= 4 and tabla & (1 << self.indice[asignacion]):
                resultado.add(unidad["id"])
        return resultado


class ReglasJuegoTest(unittest.TestCase):
    """Regresiones de balance, efectos, movimiento, CPU y validación."""

    def test_costos_y_dificultades(self):
        """El costo cuenta operadores y cada dificultad oculta el detalle requerido."""
        for dificultad, detalle in [("facil", "completo"), ("normal", "conteo"), ("dificil", "sintaxis")]:
            estado = crear_estado("local", {"azul": dificultad, "rojo": dificultad})
            vista = previsualizar(estado, "A2", "(Enemigo(x) & exists y Cerca(x,y))")
            self.assertEqual(vista["costo"], 4)
            self.assertEqual(vista["nivel_detalle"], detalle)
            self.assertTrue(vista["lectura"])
            if detalle != "completo":
                self.assertEqual(vista["objetivos"], [])
        estado["energia"]["azul"] = 1
        with self.assertRaises(ErrorValidacion):
            previsualizar(estado, "A2", "exists y Enemigo(x)")

    def test_danio_precision_victoria_y_estado_terminal_valido(self):
        """Un único objetivo recibe seis de daño y el estado ganador sigue siendo válido."""
        estado = encuentro([unidad("A1", "azul", "Infante", 1, 1),
                            unidad("R1", "rojo", "Infante", 2, 1, 6)])
        resultado = atacar(estado, "A1", "Enemigo(x)")
        self.assertEqual(resultado["estado"]["ganador"], "azul")
        self.assertEqual([e["tipo"] for e in resultado["eventos"]],
                         ["ataque", "danio", "baja", "victoria"])
        _validar_estado_completo(resultado["estado"])
        with self.assertRaisesRegex(ErrorValidacion, "terminó"):
            terminar_turno(resultado["estado"])
        self.assertEqual(estado["unidades"][1]["vida"], 6)

    def test_precision_multiple_fuego_amigo_y_cura(self):
        """La selección incluye aliados y el médico cura también enemigos sin exceder máximos."""
        estado = encuentro([unidad("A1", "azul", "Infante", 1, 1),
                            unidad("A2", "azul", "Infante", 2, 1),
                            unidad("R1", "rojo", "Infante", 1, 2)])
        resultado = atacar(estado, "A1", "Cerca(x,yo)")
        self.assertEqual([u["vida"] for u in resultado["estado"]["unidades"]], [10, 5, 5])
        estado["unidades"][0] = unidad("A1", "azul", "Medico", 1, 1)
        estado["unidades"][1]["vida"], estado["unidades"][2]["vida"] = 9, 4
        vista = previsualizar(estado, "A1", "Cerca(x,yo)")
        resultado = atacar(estado, "A1", "Cerca(x,yo)")
        self.assertEqual([u["vida"] for u in resultado["estado"]["unidades"]], [7, 10, 7])
        self.assertEqual([o["cantidad"] for o in vista["objetivos"] if o["afectado"]], [1, 3])

    def test_turno_relativo_relacion_vacia_y_variables(self):
        """Mio depende del turno y los predicados vacíos son evaluables."""
        estado = encuentro([unidad("R1", "rojo", "Infante", 2, 1),
                            unidad("A1", "azul", "Infante", 3, 1)], turno="rojo")
        self.assertEqual(previsualizar(estado, "R1", "Enemigo(x)")["resumen"]["enemigos"], 1)
        self.assertEqual(previsualizar(estado, "R1", "Mio(x)")["resumen"]["aliados"], 0)
        self.assertEqual(previsualizar(estado, "R1", "Herido(x)")["resumen"]["enemigos"], 0)
        with self.assertRaisesRegex(ErrorValidacion, "única variable libre"):
            previsualizar(estado, "R1", "Cerca(x,z)")

    def test_movimiento_agua_muro_ocupacion_y_una_vez(self):
        """El camino respeta costos, obstáculos y el uso del movimiento del turno."""
        estado = encuentro([unidad("A1", "azul", "Arquero", 3, 3),
                            unidad("R1", "rojo", "Infante", 3, 2)])
        self.assertNotIn((4, 3), posiciones_alcanzables(estado, "A1"))
        estado["mapa"]["terreno"][3][4] = "agua"
        self.assertEqual(posiciones_alcanzables(estado, "A1")[(4, 3)], 2)
        self.assertNotIn((3, 2), posiciones_alcanzables(estado, "A1"))
        movido = mover(estado, "A1", [4, 3])["estado"]
        with self.assertRaises(ErrorValidacion):
            mover(movido, "A1", [3, 3])
        self.assertEqual((estado["unidades"][0]["col"], estado["unidades"][0]["fila"]), (3, 3))

    def test_rechaza_estados_incoherentes(self):
        """Rechaza límites, muros, superposición, bandos ausentes y ganadores incoherentes."""
        original = crear_estado()
        mutaciones = [
            lambda e: e["unidades"][0].update(col=-1),
            lambda e: e["energia"].update(azul=999),
            lambda e: e["unidades"][0].pop("vida"),
            lambda e: e["unidades"][0].update(tipo=[]),
            lambda e: e["unidades"][0].update(vida=999),
            lambda e: e["unidades"][1].update(id=e["unidades"][0]["id"]),
            lambda e: e["unidades"][1].update(col=1, fila=0),
            lambda e: e["unidades"][0].update(col=4, fila=3),
            lambda e: e.update(turno="verde"),
            lambda e: e.update(unidades=e["unidades"][:4]),
            lambda e: e.update(ganador="azul"),
            lambda e: e.pop("mapa"),
        ]
        for mutar in mutaciones:
            estado = deepcopy(original)
            mutar(estado)
            with self.subTest(estado=estado):
                with self.assertRaises(ErrorValidacion):
                    previsualizar(estado, "A2", "Enemigo(x)")

    def test_cpu_determinista_y_estado_final(self):
        """La semilla reproduce acciones y el estado incluye las bajas de la CPU."""
        self.assertEqual(terminar_turno(crear_estado(semilla=43)),
                         terminar_turno(crear_estado(semilla=43)))
        estado = encuentro([unidad("A1", "azul", "Infante", 5, 4, 2),
                            unidad("R1", "rojo", "Arquero", 4, 4)], modo="cpu", dificultad="dificil")
        resultado = terminar_turno(estado)
        self.assertEqual(resultado["estado"]["ganador"], "rojo")
        self.assertNotIn("A1", {u["id"] for u in resultado["estado"]["unidades"]})

    def test_medico_no_prefiere_curar_enemigos_en_ninguna_dificultad(self):
        """Incluso con muchos aliados heridos se descarta curar también a un rival."""
        for dificultad, semilla in product(("facil", "normal", "dificil"), range(8)):
            soldados = [unidad("R1", "rojo", "Medico", 3, 4),
                        unidad("A1", "azul", "Infante", 3, 5, 2)]
            for indice, (col, fila) in enumerate([(2, 4), (4, 4), (3, 3), (2, 5)], 2):
                soldados.append(unidad(f"R{indice}", "rojo", "Tanque", col, fila, 2))
            for soldado in soldados:
                soldado["movio"] = True
            estado = encuentro(soldados, modo="cpu", dificultad=dificultad)
            estado["semilla"] = semilla
            # El cambio de turno habilita movimiento: se aísla aquí la decisión de la fórmula.
            with patch("evaluador.juego.cpu._mover_cpu", return_value=[]):
                resultado = terminar_turno(estado)
            self.assertFalse(any(e["tipo"] == "cura" and e["unidad"] == "A1"
                                 for e in resultado["eventos"]))

    def test_medico_no_cura_a_sanos(self):
        """Una plantilla que solo selecciona soldados sanos no consume energía."""
        estado = encuentro([unidad("A1", "azul", "Tanque", 8, 6),
                            unidad("R1", "rojo", "Medico", 1, 1),
                            unidad("R2", "rojo", "Tanque", 2, 1)], modo="cpu", dificultad="dificil")
        resultado = terminar_turno(estado)
        self.assertFalse(any(e["tipo"] == "cura" for e in resultado["eventos"]))

    def test_longitud_y_recursion_controladas(self):
        """Una negación enorme y una recursión del parser se convierten en errores del juego."""
        with self.assertRaisesRegex(ErrorValidacion, "300"):
            previsualizar(crear_estado(), "A2", "~" * 1100 + "Enemigo(x)")
        with patch("evaluador.juego.formulas.analizar", side_effect=RecursionError):
            with self.assertRaisesRegex(ErrorValidacion, "anidación"):
                analizar_formula("Enemigo(x)")


class TutorialTest(unittest.TestCase):
    """Las lecciones son resolubles, guiadas y exigen sus conceptos nuevos."""

    def test_practicas_retos_y_ejemplos(self):
        """Todas las soluciones y ejemplos pasan por el motor real sobre estados válidos."""
        self.assertEqual([n["id"] for n in niveles()], list(range(9)))
        for nivel in niveles():
            estado = crear_estado("tutorial", nivel=nivel["id"])
            original = deepcopy(estado)
            _validar_estado_completo(estado)
            self.assertEqual(nivel["pasos"][-1]["tipo"], "reto")
            self.assertTrue(1 <= sum(p["tipo"] == "practica" for p in nivel["pasos"]) <= 3)
            for indice, paso in enumerate(nivel["pasos"]):
                escenario = paso["estado"]
                _validar_estado_completo(escenario)
                self.assertEqual(escenario, crear_estado("tutorial", nivel=nivel["id"], paso=indice))
                if paso["tipo"] == "ejemplo":
                    vista = previsualizar(escenario, "A1", paso["formula"])
                    self.assertEqual(vista["lectura"], paso["lectura"])
                    self.assertEqual(golpea(escenario, paso["formula"]), set(paso["objetivo"]))
                    self.assertTrue(all("arbol" in o for o in vista["objetivos"]))
                if paso["tipo"] in ("practica", "reto"):
                    if paso["tipo"] == "practica":
                        self.assertEqual(len(paso["pistas"]), 3)
                    resultado = practicar(estado, nivel["id"], indice, paso["solucion"])
                    self.assertTrue(resultado["acierto"], (nivel["id"], resultado))
                    self.assertEqual(resultado["golpea"], paso["objetivo"])
                    self.assertEqual(resultado["estado"], escenario)
            self.assertEqual(estado, original)
            resultado = atacar(estado, "A1", nivel["solucion_ejemplo"])
            self.assertTrue(resultado["estado"]["nivel_completado"])
            self.assertEqual(resultado["estado"]["ganador"], "azul")
            _validar_estado_completo(resultado["estado"])

    def test_ensenanza_por_fuerza_bruta_hasta_tres_operadores(self):
        """Ninguna fórmula del vocabulario sin el símbolo nuevo selecciona exactamente S."""
        inicio = perf_counter()
        total = 0
        for nivel in niveles():
            estado = crear_estado("tutorial", nivel=nivel["id"])
            # En la lección anidada también se incluye z, la variable de su ejemplo.
            variables = ("x", "y", "z") if nivel["id"] == 8 else ("x", "y")
            busqueda = BusquedaFormulas(estado, nivel, nivel["simbolo_nuevo"], variables)
            candidatas = busqueda.generar(3)
            total += len(candidatas)
            for (tabla, libres), texto in candidatas.items():
                if libres <= {"x"}:
                    seleccion = busqueda.seleccion(tabla)
                    self.assertEqual(golpea(estado, texto), seleccion)
                    self.assertNotEqual(seleccion, set(nivel["objetivos"]), (nivel["id"], texto))
            self.assertEqual(golpea(estado, nivel["solucion_ejemplo"]), set(nivel["objetivos"]))
        duracion = perf_counter() - inicio
        print(f"\nFuerza bruta: {total} clases de fórmulas, 9 retos, <=3 operadores, {duracion:.3f} s")
        self.assertLess(duracion, 10)

    def test_vocabulario_restringido_incluye_igualdad_y_constante(self):
        """No se pueden colar igualdad, constantes, predicados ni conectivos no declarados."""
        for formula in ["x=x", "Cerca(x,yo)", "(Herido(x) | Tanque(x))", "Mio(x)"]:
            with self.assertRaisesRegex(ErrorValidacion, "no permite"):
                previsualizar(crear_estado("tutorial", nivel=5), "A1", formula)

    def test_fallo_explicito_y_estado_valido_sin_objetivos_muertos(self):
        """Un ataque incorrecto termina el intento aunque elimine a los objetivos."""
        estado = crear_estado("tutorial", nivel=3)
        resultado = atacar(estado, "A1", "(Enemigo(x) & Enemigo(x))")
        self.assertTrue(resultado["estado"]["nivel_fallido"])
        self.assertEqual(resultado["sobran"], ["R2", "R3"])
        self.assertEqual(resultado["faltan"], [])
        self.assertIn("R2", resultado["mensaje"])
        self.assertIsNone(resultado["estado"]["ganador"])
        _validar_estado_completo(resultado["estado"])
        with self.assertRaisesRegex(ErrorValidacion, "Reintenta"):
            terminar_turno(resultado["estado"])
        reinicio = crear_estado("tutorial", nivel=3)
        self.assertFalse(reinicio["nivel_fallido"])

    def test_feedback_especifico_y_practica_sin_energia(self):
        """La práctica distingue fuego amigo y omisiones, incluso con cero energía."""
        estado = crear_estado("tutorial", nivel=3)
        estado["energia"]["azul"] = 0
        resultado = practicar(estado, 3, 3, "Tanque(x)")
        self.assertEqual(resultado["sobran"], ["A4"])
        self.assertIn("tu equipo", resultado["mensaje"])
        self.assertIn("Enemigo", resultado["mensaje"])
        resultado = practicar(crear_estado("tutorial", nivel=2), 2, 4, "Arquero(x)")
        self.assertEqual(resultado["faltan"], ["R4"])
        self.assertIn("Faltó", resultado["mensaje"])

    def test_testigo_existe_no_es_el_objetivo(self):
        """La negación de existe rechaza al enemigo con un compañero nuestro cerca."""
        estado = crear_estado("tutorial", nivel=7)
        relaciones = _interpretacion(estado, "azul", "A1").relaciones
        self.assertNotIn(("R1", "R1"), relaciones["Cerca"])
        self.assertIn(("R2", "A2"), relaciones["Cerca"])
        vista = previsualizar(estado, "A1", niveles()[7]["solucion_ejemplo"])
        self.assertTrue(next(o for o in vista["objetivos"] if o["id"] == "R1")["afectado"])
        self.assertFalse(next(o for o in vista["objetivos"] if o["id"] == "R2")["afectado"])
        positiva = "exists y (Mio(y) & Cerca(x,y))"
        self.assertIn("R2", golpea(estado, positiva))
        self.assertNotIn("R1", golpea(estado, positiva))

    def test_orden_cuantificadores_y_contraejemplo(self):
        """La anidación permite testigos distintos; invertirla cambia la selección."""
        estado = crear_estado("tutorial", nivel=8)
        self.assertEqual(golpea(estado, niveles()[8]["solucion_ejemplo"]), {"R1"})
        inversa = "(Enemigo(x) & " + ORDEN_UNICO + ")"
        self.assertNotEqual(golpea(estado, inversa), {"R1"})
        vista = previsualizar(estado, "A1", niveles()[8]["solucion_ejemplo"])
        r2 = next(o for o in vista["objetivos"] if o["id"] == "R2")
        pendientes = [r2["arbol"]]
        tipos = []
        while pendientes:
            nodo = pendientes.pop()
            tipos.append(nodo["tipo"])
            pendientes.extend(nodo["hijos"])
        self.assertIn("contraejemplo", tipos)
        self.assertEqual(vista["costo"], 8)
        self.assertEqual(previsualizar(estado, "A1", inversa)["costo"], 8)

    def test_lectura_completa(self):
        """Compara frases completas para detectar contracciones y cuantificadores poco naturales."""
        casos = [
            ("(Enemigo(x) & ~Tanque(x))", "(x es enemigo) y (x no es tanque)"),
            ("(Mio(x) | Herido(x))", "(x es de tu equipo) o (x está herido)"),
            ("(Herido(x) -> Infante(x))", "si (x está herido), entonces (x es infante)"),
            ("Cerca(x,yo)", "x está cerca del atacante"),
            ("~Cerca(x,yo)", "x no está cerca del atacante"),
            ("Alineado(x,yo)", "x está alineado con el atacante"),
            ("exists y (Cerca(x,y) & Mio(y))",
             "existe algún soldado y para el que ((x está cerca de y) y (y es de tu equipo))"),
            ("forall y exists z Alineado(y,z)",
             "para cada soldado y, se cumple "
             "(existe algún soldado z para el que (y está alineado con z))"),
            ("x=yo", "x es el mismo soldado que el atacante"),
            ("~(Arquero(x) | Medico(x))", "no se cumple que ((x es arquero) o (x es médico))"),
            ("EnAgua(x)", "x está en el agua"),
        ]
        for formula, esperada in casos:
            self.assertEqual(leer_formula(formula), esperada)

    def test_progresion_sin_revelar_solucion_del_reto(self):
        """Cada práctica y ejemplo cambia la meta y el encuentro sin adelantar la respuesta final."""
        for nivel in niveles():
            reto = nivel["pasos"][-1]
            metas = []
            solucion = analizar(nivel["solucion_ejemplo"], LENGUAJE)
            for paso in nivel["pasos"][:-1]:
                texto = json.dumps(paso, ensure_ascii=False)
                self.assertNotIn(nivel["solucion_ejemplo"], texto, nivel["id"])
                for campo in ("formula", "solucion"):
                    if campo in paso:
                        self.assertNotEqual(analizar(paso[campo], LENGUAJE), solucion, nivel["id"])
                if paso["tipo"] in ("practica", "ejemplo"):
                    self.assertNotEqual(paso["objetivo"], reto["objetivo"], nivel["id"])
                    self.assertNotEqual(paso["estado"]["unidades"], reto["estado"]["unidades"])
                if paso["tipo"] == "practica":
                    self.assertNotIn(paso["objetivo"], metas)
                    metas.append(paso["objetivo"])

    def test_movimiento_bloqueado_y_concepto_obligatorio(self):
        """El atajo de mover A2 y A1 falla y copiar un predicado no basta en el reto de conjunción."""
        estado = crear_estado("tutorial", nivel=3)
        original = deepcopy(estado)
        for unidad_id, destino in [("A2", [1, 0]), ("A1", [1, 6])]:
            with self.assertRaisesRegex(ErrorValidacion, "posiciones están fijas"):
                mover(estado, unidad_id, destino)
        with self.assertRaisesRegex(ErrorValidacion, "símbolo nuevo"):
            atacar(estado, "A1", "Arquero(x)")
        self.assertEqual(estado, original)
        for nivel in niveles():
            # Siempre existe al menos un átomo permitido que omite el símbolo nuevo.
            predicado = next(p for p in nivel["predicados_permitidos"]
                             if p != "yo" and p != nivel["simbolo_nuevo"])
            argumentos = "x,x" if LENGUAJE.predicados[predicado] == 2 else "x"
            with self.assertRaisesRegex(ErrorValidacion, "símbolo nuevo"):
                atacar(crear_estado("tutorial", nivel=nivel["id"]), "A1", predicado + f"({argumentos})")
        with self.assertRaisesRegex(ErrorValidacion, "paso guiado"):
            atacar(crear_estado("tutorial", nivel=3, paso=2), "A1", "(Mio(x) & Arquero(x))")

    def test_cumplir_alcance_umbral_herido_y_bando(self):
        """Separa verdad y alcance; media vida no es Herido y el bando depende del turno."""
        estado = crear_estado("tutorial", nivel=0)
        objetivos = previsualizar(estado, "A1", "Enemigo(x)")["objetivos"]
        fuera = next(o for o in objetivos if o["id"] == "R2")
        self.assertTrue(fuera["cumple"])
        self.assertFalse(fuera["en_alcance"])
        self.assertFalse(fuera["afectado"])
        estado = niveles()[0]["pasos"][1]["estado"]
        yo = previsualizar(estado, "A1", "Mio(x)")["objetivos"][0]
        self.assertTrue(yo["cumple"])
        self.assertFalse(yo["afectado"])
        estado = niveles()[2]["pasos"][1]["estado"]
        objetivos = {o["id"]: o for o in previsualizar(estado, "A1", "Herido(x)")["objetivos"]}
        self.assertFalse(objetivos["R2"]["cumple"])  # Vida completa: 16/16.
        self.assertFalse(objetivos["R3"]["cumple"])  # Exactamente la mitad: 5/10.
        self.assertTrue(objetivos["A2"]["cumple"])  # Menos de la mitad: 2/7.
        azul = _interpretacion(estado, "azul", "A1").relaciones
        rojo = _interpretacion(estado, "rojo", "R2").relaciones
        self.assertEqual(azul["Mio"], rojo["Enemigo"])
        self.assertEqual(azul["Enemigo"], rojo["Mio"])

    def test_tabla_implicacion_y_objetivo_tactico(self):
        """La condición falsa acepta al infante enemigo sin incluir al infante aliado."""
        nivel = niveles()[5]
        self.assertEqual([fila["resultado"] for fila in nivel["tabla_verdad"]],
                         [True, True, False, True])
        estado = crear_estado("tutorial", nivel=5)
        self.assertEqual(golpea(estado, nivel["solucion_ejemplo"]), {"R1", "R2"})
        self.assertEqual(golpea(estado, "(Tanque(x) -> Herido(x))"), {"A2", "R1", "R2"})

    def test_comparacion_guiada_mismo_tablero_y_costo(self):
        """Los dos órdenes comparten escenario y costo; el universal sencillo señala un aliado lejano."""
        nivel = niveles()[8]
        ejemplos = [p for p in nivel["pasos"] if p["tipo"] == "ejemplo"]
        simple, por_vecino, unico = ejemplos
        self.assertEqual(por_vecino["estado"]["unidades"], unico["estado"]["unidades"])
        primero = previsualizar(por_vecino["estado"], "A1", ORDEN_POR_VECINO)
        segundo = previsualizar(unico["estado"], "A1", ORDEN_UNICO)
        self.assertEqual(primero["costo"], segundo["costo"])
        self.assertNotEqual(por_vecino["objetivo"], unico["objetivo"])
        vista = previsualizar(simple["estado"], "A1", simple["formula"])
        soldado = next(o for o in vista["objetivos"] if o["id"] == "R4")
        self.assertEqual(soldado["arbol"]["tipo"], "contraejemplo")
        self.assertIn("A1", soldado["arbol"]["hijos"][-1]["asignacion"])
        reto = crear_estado("tutorial", nivel=8)
        relaciones = _interpretacion(reto, "azul", "A1").relaciones
        for vecino, vigilante in [("R2", "A2"), ("R3", "A3")]:
            self.assertIn(("R1", vecino), relaciones["Cerca"])
            self.assertIn((vecino, vigilante), relaciones["Cerca"])
            self.assertNotIn((vecino, "R1"), {(a, b) for a, b in relaciones["Cerca"]
                                            if (b,) in relaciones["Mio"]})


class RutasJuegoTest(unittest.TestCase):
    """El contrato HTTP se mantiene y los cuerpos adversos nunca producen un 500."""

    def setUp(self):
        """Crea un cliente sin servidor ni dependencias externas."""
        self.cliente = app.test_client()

    def test_rutas_y_contrato_guiado(self):
        """Consulta lecciones, practica, mueve, previsualiza, ataca y cambia de turno."""
        lecciones = self.cliente.get("/api/juego/niveles").json["niveles"]
        self.assertEqual(len(lecciones), 9)
        estado = self.cliente.post("/api/juego/nueva", json={"modo": "tutorial", "nivel": 3}).json["estado"]
        practica = self.cliente.post("/api/juego/practicar", json={
            "estado": estado, "nivel": 3, "paso": 2, "formula": lecciones[3]["pasos"][2]["solucion"],
        }).json
        self.assertTrue(practica["acierto"])
        self.assertTrue({"golpea", "sobran", "faltan", "mensaje", "lectura"} <= practica.keys())
        for ruta in ("previsualizar", "atacar"):
            respuesta = self.cliente.post("/api/juego/" + ruta, json={
                "estado": estado, "atacante": "A1", "formula": lecciones[3]["solucion_ejemplo"],
            })
            self.assertTrue(respuesta.json["ok"])
        estado = crear_estado("local")
        self.assertTrue(self.cliente.post("/api/juego/mover", json={
            "estado": estado, "unidad": "A1", "destino": [2, 0],
        }).json["ok"])
        self.assertTrue(self.cliente.post("/api/juego/terminar_turno", json={"estado": estado}).json["ok"])
        pagina = self.cliente.get("/juego")
        self.assertEqual(pagina.status_code, 200)
        pagina.close()

    def test_escenarios_por_paso_y_atajos_rechazados_por_http(self):
        """El cliente puede cargar cualquier paso y el motor rechaza movimiento y atajos de fórmula."""
        for nivel in niveles():
            for indice, paso in enumerate(nivel["pasos"]):
                respuesta = self.cliente.post("/api/juego/nueva", json={
                    "modo": "tutorial", "nivel": nivel["id"], "paso": indice,
                }).json
                self.assertTrue(respuesta["ok"])
                self.assertEqual(respuesta["estado"], paso["estado"])
        estado = crear_estado("tutorial", nivel=3)
        for ruta, campos in [("mover", {"unidad": "A2", "destino": [1, 0]}),
                             ("atacar", {"atacante": "A1", "formula": "Arquero(x)"})]:
            respuesta = self.cliente.post("/api/juego/" + ruta, json={"estado": estado, **campos})
            self.assertFalse(respuesta.json["ok"])
        for paso in (-1, 999, True, [], "2"):
            respuesta = self.cliente.post("/api/juego/nueva",
                                          json={"modo": "tutorial", "nivel": 3, "paso": paso})
            self.assertFalse(respuesta.json["ok"])

    def test_cuerpos_raros_en_todas_las_rutas(self):
        """Cada ruta POST rechaza cuerpos no objeto, campos raros y JSON malformado."""
        rutas = ("nueva", "mover", "previsualizar", "atacar", "terminar_turno", "practicar")
        cuerpos = [None, [], ["x"], 1, True, "texto", {}, {"estado": []},
                   {"modo": [], "nivel": {}, "dificultad": "facil"}]
        for ruta, cuerpo in product(rutas, cuerpos):
            respuesta = self.cliente.post("/api/juego/" + ruta, data=json.dumps(cuerpo),
                                          content_type="application/json")
            self.assertLess(respuesta.status_code, 500, (ruta, cuerpo))
            if ruta == "nueva" and cuerpo in ({}, {"estado": []}):
                self.assertTrue(respuesta.json["ok"])
            else:
                self.assertFalse(respuesta.json["ok"], (ruta, cuerpo))
        for ruta in rutas:
            for cuerpo in ("{", "[" * 1500 + "]" * 1500):
                respuesta = self.cliente.post("/api/juego/" + ruta, data=cuerpo,
                                              content_type="application/json")
                self.assertLess(respuesta.status_code, 500)
                self.assertFalse(respuesta.json["ok"])

    def test_tipos_adversos_de_cada_campo_del_estado_en_todas_las_acciones(self):
        """Sustituye campos anidados por tipos JSON incompatibles en cada acción."""
        base = crear_estado()
        caminos = [
            ("modo",), ("turno",), ("numero_turno",), ("ganador",), ("energia",),
            ("dificultad",), ("mapa",), ("unidades",), ("semilla",),
            ("energia", "azul"), ("dificultad", "azul"), ("mapa", "terreno"),
        ] + [("unidades", 0, campo) for campo in base["unidades"][0]]
        rutas = ("mover", "previsualizar", "atacar", "terminar_turno", "practicar")
        for ruta, camino, valor in product(rutas, caminos, (None, [], {}, "raro", True, 1.2)):
            estado = deepcopy(base)
            destino = estado
            for clave in camino[:-1]:
                destino = destino[clave]
            destino[camino[-1]] = valor
            datos = {"estado": estado, "unidad": "A1", "destino": [2, 0],
                     "atacante": "A2", "formula": "Enemigo(x)", "nivel": 0, "paso": 2}
            respuesta = self.cliente.post("/api/juego/" + ruta, json=datos)
            self.assertLess(respuesta.status_code, 500, (ruta, camino, valor))
            if not respuesta.json["ok"]:
                self.assertEqual(set(respuesta.json["errores"][0]),
                                 {"origen", "categoria", "mensaje", "posicion"})

    def test_formulas_enormes_y_campos_de_practica_invalidos(self):
        """La regresión de recursión se controla en preview, ataque y práctica."""
        estado = crear_estado("tutorial", nivel=0)
        for ruta, formula in product(("previsualizar", "atacar", "practicar"),
                                    ("~" * 1100 + "Enemigo(x)", [], {}, 7, None)):
            respuesta = self.cliente.post("/api/juego/" + ruta, json={
                "estado": estado, "atacante": "A1", "formula": formula, "nivel": 0, "paso": 2,
            })
            self.assertLess(respuesta.status_code, 500)
            self.assertFalse(respuesta.json["ok"])
        for campo, valor in [("nivel", 9), ("nivel", True), ("paso", -1), ("paso", 0), ("paso", 99)]:
            datos = {"estado": estado, "nivel": 0, "paso": 2, "formula": "Enemigo(x)"}
            datos[campo] = valor
            respuesta = self.cliente.post("/api/juego/practicar", json=datos)
            self.assertFalse(respuesta.json["ok"])


if __name__ == "__main__":
    unittest.main()
