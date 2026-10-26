import unittest

from evaluador import Categoria, ErrorValidacion, Interpretacion, Lenguaje, analizar, evaluar, variables_libres

# L = {c (cte), s (unaria), P (unario), R (binario)}; D = {0, 1, 2}
# s es el sucesor módulo 3, P = "es par" = {0, 2}, R = "menor que".
L = Lenguaje(funciones={"c": 0, "s": 1}, predicados={"P": 1, "R": 2})
D = ["0", "1", "2"]
I = Interpretacion(
    L, D,
    funciones={"c": {(): "0"}, "s": {("0",): "1", ("1",): "2", ("2",): "0"}},
    relaciones={"P": {("0",), ("2",)}, "R": {("0", "1"), ("0", "2"), ("1", "2")}},
)


def categoria(fn):
    try:
        fn()
    except ErrorValidacion as e:
        return e.problemas[0].categoria
    raise AssertionError("se esperaba ErrorValidacion")


class TestSintaxis(unittest.TestCase):
    def test_formulas_validas(self):
        for texto in ["P(c)", "¬P(x)", "(P(x) ∧ R(x, y))", "∀x ∃y R(x, y)", "s(s(c)) = x",
                      "forall x (P(x) -> exists y R(x, y))", "~(P(x) | !P(x))", "∀x(P(x) /\\ P(s(x)))"]:
            with self.subTest(texto=texto):
                analizar(texto, L)

    def test_parentesis_estrictos(self):
        self.assertEqual(categoria(lambda: analizar("P(x) ∧ P(y)", L)), Categoria.SINTAXIS)
        self.assertEqual(categoria(lambda: analizar("(P(x) ∧ P(y) ∧ P(c))", L)), Categoria.SINTAXIS)
        self.assertEqual(categoria(lambda: analizar("(P(x))", L)), Categoria.SINTAXIS)
        self.assertEqual(categoria(lambda: analizar("(P(x) ∧ P(y)", L)), Categoria.SINTAXIS)
        self.assertEqual(categoria(lambda: analizar("∀xP(x)", L)), Categoria.SINTAXIS)

    def test_simbolos_y_aridades(self):
        self.assertEqual(categoria(lambda: analizar("Q(x)", L)), Categoria.SIMBOLO)
        self.assertEqual(categoria(lambda: analizar("(P(x) ↔ P(y))", L)), Categoria.SIMBOLO)
        self.assertEqual(categoria(lambda: analizar("R(x)", L)), Categoria.ARIDAD)
        self.assertEqual(categoria(lambda: analizar("P(s(x, y))", L)), Categoria.ARIDAD)
        self.assertEqual(categoria(lambda: analizar("P(c(x))", L)), Categoria.ARIDAD)
        self.assertEqual(categoria(lambda: analizar("∀c P(c)", L)), Categoria.SIMBOLO)
        self.assertEqual(categoria(lambda: analizar("P(P(x))", L)), Categoria.SIMBOLO)

    def test_variables_libres(self):
        f = analizar("(∀x R(x, y) ∧ ∃z (P(z) ∨ P(x)))", L)
        self.assertEqual(variables_libres(f), ["y", "x"])
        self.assertEqual(variables_libres(analizar("∀x ∃y R(x, y)", L)), [])


class TestInterpretacion(unittest.TestCase):
    def test_errores(self):
        crear = lambda **kw: Interpretacion(L, kw.get("D", D), kw.get("f", I.funciones), kw.get("r", I.relaciones))
        self.assertEqual(categoria(lambda: crear(D=[])), Categoria.DOMINIO)
        self.assertEqual(categoria(lambda: crear(D=["0", "0"])), Categoria.DOMINIO)
        parcial = {**I.funciones, "s": {("0",): "1"}}
        self.assertEqual(categoria(lambda: crear(f=parcial)), Categoria.TUPLA)
        fuera = {**I.funciones, "c": {(): "9"}}
        self.assertEqual(categoria(lambda: crear(f=fuera)), Categoria.DOMINIO)
        self.assertEqual(categoria(lambda: crear(r={**I.relaciones, "P": set()})), Categoria.TUPLA)
        self.assertEqual(categoria(lambda: crear(r={**I.relaciones, "R": {("0",)}})), Categoria.ARIDAD)

    def test_lenguaje_invalido(self):
        self.assertEqual(categoria(lambda: Lenguaje({"f": 1}, {"f": 1})), Categoria.LENGUAJE)
        self.assertEqual(categoria(lambda: Lenguaje({}, {"P": 0})), Categoria.ARIDAD)


class TestSemantica(unittest.TestCase):
    def test_atomicas_y_conectivos(self):
        self.assertTrue(evaluar("P(c)", L, I).valor)
        self.assertFalse(evaluar("P(s(c))", L, I).valor)
        self.assertTrue(evaluar("s(s(s(c))) = c", L, I).valor)
        self.assertTrue(evaluar("(P(s(c)) → P(c))", L, I).valor)
        self.assertFalse(evaluar("(P(c) → P(s(c)))", L, I).valor)

    def test_testigo_y_contraejemplo(self):
        r = evaluar("∃x ¬P(x)", L, I)
        self.assertTrue(r.valor)
        self.assertEqual(r.arbol.tipo, "testigo")
        self.assertIn("x ↦ 1", r.arbol.explicacion)
        # recorrido tipo for: x ↦ 0 (falso) y se detiene en x ↦ 1 (verdadero)
        self.assertEqual([h.asignacion for h in r.arbol.hijos], ["x ↦ 0", "x ↦ 1"])
        self.assertEqual([h.valor for h in r.arbol.hijos], [False, True])

        r = evaluar("∀x P(x)", L, I)
        self.assertFalse(r.valor)
        self.assertEqual(r.arbol.tipo, "contraejemplo")
        self.assertIn("x ↦ 1", r.arbol.explicacion)
        self.assertEqual([h.valor for h in r.arbol.hijos], [True, False])

    def test_comprobacion_completa(self):
        r = evaluar("∀x ¬R(x, x)", L, I)
        self.assertTrue(r.valor)
        self.assertEqual(r.arbol.tipo, "comprobacion")
        self.assertEqual(len(r.arbol.hijos), len(D))

        r = evaluar("∃x R(x, c)", L, I)
        self.assertFalse(r.valor)
        self.assertEqual(len(r.arbol.hijos), len(D))

    def test_entorno(self):
        self.assertTrue(evaluar("R(x, y)", L, I, {"x": "0", "y": "2"}).valor)
        self.assertEqual(categoria(lambda: evaluar("R(x, y)", L, I, {"x": "0"})), Categoria.ASIGNACION)
        self.assertEqual(categoria(lambda: evaluar("P(x)", L, I, {"x": "7"})), Categoria.ASIGNACION)
        # la variable ligada sombrea al entorno
        self.assertFalse(evaluar("(P(x) ∧ ∀x P(x))", L, I, {"x": "0"}).valor)


if __name__ == "__main__":
    unittest.main()
