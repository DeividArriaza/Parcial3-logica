"""Contrato de fórmulas cerradas, constantes y selección explícita de objetivos."""
from copy import deepcopy
import unittest

from app import app
from evaluador.errores import ErrorValidacion
from evaluador.juego import atacar, crear_estado, niveles, practicar, previsualizar
from evaluador.juego.cpu import _plantillas
from evaluador.juego.formulas import analizar_formula
from evaluador.sintaxis import variables_libres


class FormulasCerradasTest(unittest.TestCase):
    def setUp(self):
        self.estado = crear_estado("local", {"azul": "facil", "rojo": "facil"})
        # Dos rivales en alcance permiten distinguir selección y ataque de grupo.
        unidades = self.estado["unidades"]
        self.atacante = next(u for u in unidades if u["id"] == "A2")
        self.atacante.update(col=2, fila=2)
        next(u for u in unidades if u["id"] == "R1").update(col=3, fila=2)
        next(u for u in unidades if u["id"] == "R2").update(col=2, fila=3)
        self.original = deepcopy(self.estado)

    def test_rechaza_todas_las_variables_libres_sin_mutar_estado(self):
        for formula in ("Enemigo(x)", "Cerca(objetivo,y)",
                        "(Enemigo(x) & exists y Cerca(x,y))", "forall y Cerca(x,y)"):
            for accion in (previsualizar, atacar):
                with self.subTest(formula=formula, accion=accion.__name__):
                    with self.assertRaisesRegex(ErrorValidacion, "variables libres"):
                        accion(self.estado, "A2", formula)
        self.assertEqual(self.estado, self.original)

    def test_objetivo_es_constante_y_solo_recibe_efecto_el_elegido(self):
        formula = "Enemigo(objetivo)"
        self.assertEqual(variables_libres(analizar_formula(formula)), [])
        vista = previsualizar(self.estado, "A2", formula, "R1")
        self.assertEqual([o["id"] for o in vista["objetivos"] if o["afectado"]], ["R1"])
        self.assertTrue(all(o["constantes"] == {"yo": "A2", "objetivo": "R1"}
                            for o in vista["objetivos"]))
        resultado = atacar(self.estado, "A2", formula, "R1")
        danios = [e for e in resultado["eventos"] if e["tipo"] == "danio"]
        self.assertEqual([(e["unidad"], e["cantidad"]) for e in danios], [("R1", 5)])
        self.assertEqual(next(u for u in resultado["estado"]["unidades"] if u["id"] == "R2")["vida"], 7)
        self.assertEqual(self.estado, self.original)

    def test_cuantificadores_y_formula_falsa_respetan_el_objetivo(self):
        # A2 es un testigo de nuestro equipo a una casilla de R1.
        formula = "exists y (Mio(y) & Cerca(objetivo,y))"
        vista = previsualizar(self.estado, "A2", formula, "R1")
        self.assertEqual(vista["resumen"], {"enemigos": 1, "aliados": 0})
        falsa = previsualizar(self.estado, "A2", "Mio(objetivo)", "R1")
        self.assertFalse(any(o["afectado"] for o in falsa["objetivos"]))
        cerrada = previsualizar(self.estado, "A2", "forall x (Mio(x) | Enemigo(x))", "R1")
        self.assertEqual(cerrada["resumen"]["enemigos"], 1)

    def test_grupo_interpreta_la_constante_por_soldado(self):
        vista = previsualizar(self.estado, "A2", "Enemigo(objetivo)")
        self.assertGreaterEqual(vista["resumen"]["enemigos"], 2)
        self.assertTrue(all(o["constantes"]["objetivo"] == o["id"] for o in vista["objetivos"]))

    def test_tutorial_y_cpu_publican_solo_formulas_cerradas(self):
        for nivel in niveles():
            formulas = [nivel["solucion_ejemplo"]]
            for paso in nivel["pasos"]:
                formulas.extend(paso[k] for k in ("formula", "solucion") if k in paso)
            for formula in formulas:
                with self.subTest(nivel=nivel["id"], formula=formula):
                    self.assertEqual(variables_libres(analizar_formula(formula)), [])
        for unidad in self.estado["unidades"]:
            for formula in _plantillas(unidad):
                self.assertEqual(variables_libres(analizar_formula(formula)), [])
        estado = crear_estado("tutorial", nivel=0, paso=3)
        with self.assertRaisesRegex(ErrorValidacion, "variables libres"):
            practicar(estado, 0, 3, "Mio(x)")
        with self.assertRaisesRegex(ErrorValidacion, "grupo del ejercicio"):
            previsualizar(estado, "A1", "Mio(objetivo)", "A3")
        with self.assertRaisesRegex(ErrorValidacion, "variables libres"):
            atacar(crear_estado("tutorial", nivel=0), "A1", "Enemigo(x)")
        respuesta = app.test_client().post("/api/juego/practicar", json={
            "estado": estado, "nivel": 0, "paso": 3, "formula": "Mio(x)",
        }).get_json()
        self.assertFalse(respuesta["ok"])
        self.assertIn("variables libres", respuesta["errores"][0]["mensaje"])

    def test_http_rechaza_variables_libres_y_objetivos_invalidos(self):
        cliente = app.test_client()
        for ruta in ("previsualizar", "atacar"):
            base = {"estado": self.estado, "atacante": "A2", "objetivo": "R1"}
            abierta = cliente.post("/api/juego/" + ruta, json={**base, "formula": "Enemigo(x)"}).get_json()
            self.assertFalse(abierta["ok"])
            self.assertIn("variables libres", abierta["errores"][0]["mensaje"])
            valida = cliente.post("/api/juego/" + ruta, json={**base, "formula": "Enemigo(objetivo)"}).get_json()
            self.assertTrue(valida["ok"])
            invalida = cliente.post("/api/juego/" + ruta, json={**base, "objetivo": "NO_EXISTE", "formula": "Enemigo(objetivo)"}).get_json()
            self.assertFalse(invalida["ok"])
            tipo = cliente.post("/api/juego/" + ruta, json={**base, "objetivo": [], "formula": "Enemigo(objetivo)"})
            self.assertEqual(tipo.status_code, 400)


if __name__ == "__main__":
    unittest.main()
