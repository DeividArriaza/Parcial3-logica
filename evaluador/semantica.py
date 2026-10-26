"""Evaluación semántica con justificación (Req. 6).

Cada evaluación produce un árbol de `Paso` que solo conserva las razones
decisivas:
- ∃ verdadero → testigo;      ∀ falso → contraejemplo;
- ∀ verdadero / ∃ falso → comprobación completa sobre todo D.

Un cuantificador se evalúa como un ciclo sobre D: ∀ se detiene en la primera
instancia falsa y ∃ en la primera verdadera. Sus hijos son las instancias
recorridas, en orden, de modo que la última es la decisiva.
"""
from dataclasses import dataclass, field

from .interpretacion import Interpretacion
from .lenguaje import Lenguaje
from .sintaxis import (EXISTE, IMPLICA, O, PARA_TODO, Y, Aplicacion, Binaria, Cuantificador, Formula, Igualdad,
                       Negacion, Predicado, Termino, Variable, analizar, variables_libres)


def valor_texto(v: bool) -> str:
    return "Verdadero" if v else "Falso"


def entorno_texto(entorno: dict[str, str]) -> str:
    if not entorno:
        return "σ = ∅"
    return "σ = {" + ", ".join(f"{x} ↦ {d}" for x, d in entorno.items()) + "}"


@dataclass
class Paso:
    formula: str
    valor: bool
    explicacion: str
    tipo: str  # atomica, negacion, conjuncion, disyuncion, implicacion, testigo, contraejemplo, comprobacion
    hijos: list["Paso"] = field(default_factory=list)
    asignacion: str | None = None  # "x ↦ d" cuando el paso es una instancia de un cuantificador

    def como_texto(self, nivel: int = 0) -> str:
        sangria = "  " * nivel
        instancia = f"[{self.asignacion}] " if self.asignacion else ""
        lineas = [f"{sangria}• {instancia}{self.formula}  ⇒  {valor_texto(self.valor)}: {self.explicacion}"]
        lineas += [h.como_texto(nivel + 1) for h in self.hijos]
        return "\n".join(lineas)

    def como_dict(self) -> dict:
        return {"formula": self.formula, "valor": self.valor, "explicacion": self.explicacion,
                "tipo": self.tipo, "asignacion": self.asignacion, "hijos": [h.como_dict() for h in self.hijos]}


@dataclass
class Resultado:
    formula: Formula
    libres: list[str]
    entorno: dict[str, str]
    arbol: Paso

    @property
    def valor(self) -> bool:
        return self.arbol.valor


class Evaluador:
    def __init__(self, interpretacion: Interpretacion):
        self.I = interpretacion

    # ------------------------------------------------------------ términos

    def termino(self, t: Termino, entorno: dict[str, str]) -> str:
        if isinstance(t, Variable):
            return entorno[t.nombre]
        args = tuple(self.termino(a, entorno) for a in t.argumentos)
        return self.I.funciones[t.funcion][args]

    def traza_termino(self, t: Termino, entorno: dict[str, str]) -> str:
        """Ej.: 'f(x, c) = f(2, 1) = 3'."""
        valor = self.termino(t, entorno)
        if isinstance(t, Variable):
            return f"{t} = {valor}"
        if not t.argumentos:
            return f"{t}ᴵ = {valor}"
        intermedio = f"{t.funcion}({', '.join(self.termino(a, entorno) for a in t.argumentos)})"
        return f"{t} = {intermedio} = {valor}"

    # ------------------------------------------------------------ fórmulas

    def evaluar(self, f: Formula, entorno: dict[str, str]) -> Paso:
        match f:
            case Predicado(nombre, args):
                valores = tuple(self.termino(a, entorno) for a in args)
                trazas = [self.traza_termino(a, entorno) for a in args]
                pertenece = valores in self.I.relaciones[nombre]
                simbolo = "∈" if pertenece else "∉"
                tupla = f"({', '.join(valores)})" if len(valores) > 1 else valores[0]
                return Paso(str(f), pertenece, f"{'; '.join(trazas)}; {tupla} {simbolo} {nombre}ᴵ", "atomica")

            case Igualdad(izq, der):
                a, b = self.termino(izq, entorno), self.termino(der, entorno)
                relacion = "=" if a == b else "≠"
                return Paso(str(f), a == b, f"{self.traza_termino(izq, entorno)}; {self.traza_termino(der, entorno)}; "
                                            f"{a} {relacion} {b}", "atomica")

            case Negacion(sub):
                hijo = self.evaluar(sub, entorno)
                return Paso(str(f), not hijo.valor, f"la subfórmula {sub} es {valor_texto(hijo.valor)}",
                            "negacion", [hijo])

            case Binaria(conectivo, izq, der):
                return self._binaria(f, conectivo, self.evaluar(izq, entorno), self.evaluar(der, entorno))

            case Cuantificador(q, x, cuerpo):
                return self._cuantificador(f, q, x, cuerpo, entorno)

    def _binaria(self, f: Binaria, conectivo: str, a: Paso, b: Paso) -> Paso:
        texto = str(f)
        if conectivo == Y:
            if a.valor and b.valor:
                return Paso(texto, True, "ambos conyuntos son verdaderos", "conjuncion", [a, b])
            falso = a if not a.valor else b
            return Paso(texto, False, f"el conyunto {falso.formula} es falso", "conjuncion", [falso])
        if conectivo == O:
            if a.valor or b.valor:
                verdadero = a if a.valor else b
                return Paso(texto, True, f"el disyunto {verdadero.formula} es verdadero", "disyuncion", [verdadero])
            return Paso(texto, False, "ambos disyuntos son falsos", "disyuncion", [a, b])
        assert conectivo == IMPLICA
        if not a.valor:
            return Paso(texto, True, "el antecedente es falso", "implicacion", [a])
        if b.valor:
            return Paso(texto, True, "el consecuente es verdadero", "implicacion", [b])
        return Paso(texto, False, "el antecedente es verdadero y el consecuente es falso", "implicacion", [a, b])

    def _cuantificador(self, f: Cuantificador, q: str, x: str, cuerpo: Formula, entorno: dict[str, str]) -> Paso:
        texto = str(f)
        buscado = q == EXISTE  # valor que decide: ∃ busca verdadero, ∀ busca falso
        total = len(self.I.dominio)
        recorrido = []
        for d in self.I.dominio:
            paso = self.evaluar(cuerpo, {**entorno, x: d})
            paso.asignacion = f"{x} ↦ {d}"
            recorrido.append(paso)
            if paso.valor == buscado:
                revisados = f"se revisaron {len(recorrido)} de {total} elemento(s)"
                if q == EXISTE:
                    return Paso(texto, True, f"testigo {x} ↦ {d} satisface {cuerpo} ({revisados})",
                                "testigo", recorrido)
                return Paso(texto, False, f"contraejemplo {x} ↦ {d} no satisface {cuerpo} ({revisados})",
                            "contraejemplo", recorrido)
        elementos = ", ".join(self.I.dominio)
        if q == PARA_TODO:
            return Paso(texto, True, f"comprobación completa: {cuerpo} es verdadera para todo {x} ∈ {{{elementos}}}",
                        "comprobacion", recorrido)
        return Paso(texto, False, f"comprobación completa: {cuerpo} es falsa para todo {x} ∈ {{{elementos}}}",
                    "comprobacion", recorrido)


def evaluar(texto: str, lenguaje: Lenguaje, interpretacion: Interpretacion,
            entorno: dict[str, str] | None = None) -> Resultado:
    """Punto de entrada: analiza, valida el entorno y evalúa. Lanza ErrorValidacion ante cualquier error."""
    formula = analizar(texto, lenguaje)
    libres = variables_libres(formula)
    sigma = interpretacion.validar_entorno(libres, entorno or {})
    arbol = Evaluador(interpretacion).evaluar(formula, sigma)
    return Resultado(formula, libres, sigma, arbol)
