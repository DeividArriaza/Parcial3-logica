"""Análisis léxico y sintáctico de fórmulas (Req. 3, 4 y 7).

Gramática (sintaxis formal estricta; los paréntesis son símbolos lógicos):

    φ ::= P(t1, ..., tn) | t1 = t2
        | ¬φ | (φ ∧ ψ) | (φ ∨ ψ) | (φ → ψ)
        | ∀x φ | ∃x φ
    t ::= x | c | f(t1, ..., tn)

Toda fórmula binaria va entre paréntesis; ¬, ∀ y ∃ no los llevan.
"""
from dataclasses import dataclass

from .errores import Categoria, ErrorValidacion
from .lenguaje import IDENTIFICADOR, Lenguaje

# ---------------------------------------------------------------- AST: términos


@dataclass(frozen=True)
class Variable:
    nombre: str

    def __str__(self) -> str:
        return self.nombre


@dataclass(frozen=True)
class Aplicacion:
    """f(t1, ..., tn); con n = 0 es una constante."""
    funcion: str
    argumentos: tuple

    def __str__(self) -> str:
        if not self.argumentos:
            return self.funcion
        return f"{self.funcion}({', '.join(map(str, self.argumentos))})"


Termino = Variable | Aplicacion

# ---------------------------------------------------------------- AST: fórmulas

NO, Y, O, IMPLICA, PARA_TODO, EXISTE = "¬", "∧", "∨", "→", "∀", "∃"


@dataclass(frozen=True)
class Predicado:
    nombre: str
    argumentos: tuple

    def __str__(self) -> str:
        return f"{self.nombre}({', '.join(map(str, self.argumentos))})"


@dataclass(frozen=True)
class Igualdad:
    izquierda: Termino
    derecha: Termino

    def __str__(self) -> str:
        return f"{self.izquierda} = {self.derecha}"


@dataclass(frozen=True)
class Negacion:
    subformula: "Formula"

    def __str__(self) -> str:
        return f"¬{self.subformula}"


@dataclass(frozen=True)
class Binaria:
    conectivo: str  # Y, O, IMPLICA
    izquierda: "Formula"
    derecha: "Formula"

    def __str__(self) -> str:
        return f"({self.izquierda} {self.conectivo} {self.derecha})"


@dataclass(frozen=True)
class Cuantificador:
    cuantificador: str  # PARA_TODO, EXISTE
    variable: str
    cuerpo: "Formula"

    def __str__(self) -> str:
        return f"{self.cuantificador}{self.variable} {self.cuerpo}"


Formula = Predicado | Igualdad | Negacion | Binaria | Cuantificador

# ---------------------------------------------------------------- variables libres


def variables_termino(t: Termino) -> list[str]:
    if isinstance(t, Variable):
        return [t.nombre]
    return [v for a in t.argumentos for v in variables_termino(a)]


def variables_libres(f: Formula) -> list[str]:
    """Variables libres en orden de primera aparición, sin repetir."""
    match f:
        case Predicado(_, args):
            encontradas = [v for a in args for v in variables_termino(a)]
        case Igualdad(izq, der):
            encontradas = variables_termino(izq) + variables_termino(der)
        case Negacion(sub):
            encontradas = variables_libres(sub)
        case Binaria(_, izq, der):
            encontradas = variables_libres(izq) + variables_libres(der)
        case Cuantificador(_, x, cuerpo):
            encontradas = [v for v in variables_libres(cuerpo) if v != x]
    return list(dict.fromkeys(encontradas))

# ---------------------------------------------------------------- análisis léxico


@dataclass(frozen=True)
class Token:
    tipo: str
    valor: str
    posicion: int


PAR_IZQ, PAR_DER, COMA, IGUAL, IDENT, FIN = "(", ")", ",", "=", "IDENT", "FIN"

# Formas aceptadas desde teclado; las de varios caracteres van primero.
_SIMBOLOS = [
    ("->", IMPLICA), ("=>", IMPLICA), ("/\\", Y), ("\\/", O),
    ("¬", NO), ("~", NO), ("!", NO),
    ("∧", Y), ("&", Y), ("∨", O), ("|", O), ("→", IMPLICA),
    ("∀", PARA_TODO), ("∃", EXISTE),
    ("(", PAR_IZQ), (")", PAR_DER), (",", COMA), ("=", IGUAL),
]
_PALABRAS = {"forall": PARA_TODO, "exists": EXISTE}
_NO_DEFINIDOS = ["<->", "<=>", "↔", "⇔", "⊤", "⊥", "⊕"]


def tokenizar(texto: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(texto):
        if texto[i].isspace():
            i += 1
            continue
        for simbolo in _NO_DEFINIDOS:
            if texto.startswith(simbolo, i):
                raise ErrorValidacion.uno(
                    Categoria.SIMBOLO,
                    f"'{simbolo}' no es un símbolo lógico de este lenguaje (solo ¬ ∧ ∨ → ∀ ∃ = ( ))", i)
        for simbolo, tipo in _SIMBOLOS:
            if texto.startswith(simbolo, i):
                tokens.append(Token(tipo, simbolo, i))
                i += len(simbolo)
                break
        else:
            m = IDENTIFICADOR.match(texto, i)
            if not m:
                raise ErrorValidacion.uno(Categoria.SIMBOLO, f"Carácter no reconocido '{texto[i]}'", i)
            palabra = m.group()
            tokens.append(Token(_PALABRAS.get(palabra, IDENT), palabra, i))
            i = m.end()
    tokens.append(Token(FIN, "", len(texto)))
    return tokens

# ---------------------------------------------------------------- análisis sintáctico


def analizar(texto: str, lenguaje: Lenguaje) -> Formula:
    """Convierte el texto en un AST o lanza ErrorValidacion."""
    if not texto.strip():
        raise ErrorValidacion.uno(Categoria.SINTAXIS, "La fórmula está vacía")
    return _Parser(tokenizar(texto), lenguaje).formula_completa()


def _describir(t: Token) -> str:
    return "el final de la fórmula" if t.tipo == FIN else f"'{t.valor}'"


class _Parser:
    def __init__(self, tokens: list[Token], lenguaje: Lenguaje):
        self.tokens = tokens
        self.i = 0
        self.lenguaje = lenguaje

    @property
    def actual(self) -> Token:
        return self.tokens[self.i]

    def avanzar(self) -> Token:
        t = self.tokens[self.i]
        self.i += 1
        return t

    def error(self, mensaje: str, token: Token | None = None, categoria=Categoria.SINTAXIS):
        raise ErrorValidacion.uno(categoria, mensaje, (token or self.actual).posicion)

    def esperar(self, tipo: str, mensaje: str) -> Token:
        if self.actual.tipo != tipo:
            self.error(f"{mensaje}; se encontró {_describir(self.actual)}")
        return self.avanzar()

    def formula_completa(self) -> Formula:
        f = self.formula()
        t = self.actual
        if t.tipo in (Y, O, IMPLICA):
            self.error(f"Las fórmulas binarias deben ir entre paréntesis: (φ {t.tipo} ψ)")
        if t.tipo != FIN:
            self.error(f"Sobra {_describir(t)} después de una fórmula completa")
        return f

    def formula(self) -> Formula:
        t = self.actual
        if t.tipo == NO:
            self.avanzar()
            return Negacion(self.formula())
        if t.tipo in (PARA_TODO, EXISTE):
            self.avanzar()
            variable = self.variable_ligada(t.tipo)
            return Cuantificador(t.tipo, variable, self.formula())
        if t.tipo == PAR_IZQ:
            self.avanzar()
            izquierda = self.formula()
            conectivo = self.actual
            if conectivo.tipo not in (Y, O, IMPLICA):
                if conectivo.tipo == PAR_DER:
                    self.error("Paréntesis innecesarios: solo se escriben alrededor de fórmulas "
                               "binarias (φ ∧ ψ), (φ ∨ ψ), (φ → ψ)")
                self.error(f"Se esperaba un conectivo binario (∧, ∨, →); se encontró {_describir(conectivo)}")
            self.avanzar()
            derecha = self.formula()
            if self.actual.tipo in (Y, O, IMPLICA):
                self.error("Cada fórmula binaria lleva sus propios paréntesis: ((φ ∘ ψ) ∘ χ)")
            self.esperar(PAR_DER, "Falta ')' para cerrar la fórmula binaria")
            return Binaria(conectivo.tipo, izquierda, derecha)
        if t.tipo == IDENT:
            return self.atomica()
        self.error(f"Se esperaba una fórmula; se encontró {_describir(t)}")

    def variable_ligada(self, cuantificador: str) -> str:
        t = self.actual
        if t.tipo != IDENT:
            self.error(f"Después de {cuantificador} debe ir una variable; se encontró {_describir(t)}")
        if self.lenguaje.es_simbolo(t.valor):
            self.error(f"'{t.valor}' es un símbolo del lenguaje, no una variable", t, Categoria.SIMBOLO)
        self.avanzar()
        if self.actual.tipo == PAR_IZQ:
            # "∀xP(x)" se lee como la variable "xP": se sugiere separar.
            for corte in range(1, len(t.valor)):
                variable, simbolo = t.valor[:corte], t.valor[corte:]
                if self.lenguaje.es_simbolo(simbolo):
                    self.error(f"'{t.valor}' se leyó como una sola variable; separe con un espacio: "
                               f"{cuantificador}{variable} {simbolo}(...)", t)
        return t.valor

    def atomica(self) -> Formula:
        t = self.actual
        if self.lenguaje.es_predicado(t.valor):
            self.avanzar()
            return Predicado(t.valor, self.argumentos(t, self.lenguaje.predicados[t.valor]))
        izquierda = self.termino()
        if self.actual.tipo != IGUAL:
            if isinstance(izquierda, Variable) and self.actual.tipo == PAR_IZQ:
                self.error(f"'{t.valor}' no está declarado como predicado ni como función", t, Categoria.SIMBOLO)
            self.error(f"'{izquierda}' es un término; para formar una fórmula atómica use un "
                       f"predicado o una igualdad t1 = t2", t)
        self.avanzar()
        return Igualdad(izquierda, self.termino())

    def termino(self) -> Termino:
        t = self.actual
        if t.tipo != IDENT:
            self.error(f"Se esperaba un término; se encontró {_describir(t)}")
        if self.lenguaje.es_predicado(t.valor):
            self.error(f"'{t.valor}' es un predicado y no puede usarse como término", t, Categoria.SIMBOLO)
        self.avanzar()
        if self.lenguaje.es_funcion(t.valor):
            aridad = self.lenguaje.funciones[t.valor]
            if aridad == 0:
                if self.actual.tipo == PAR_IZQ:
                    self.error(f"'{t.valor}' es una constante (aridad 0) y no lleva argumentos",
                               t, Categoria.ARIDAD)
                return Aplicacion(t.valor, ())
            return Aplicacion(t.valor, self.argumentos(t, aridad))
        if self.actual.tipo == PAR_IZQ:
            self.error(f"'{t.valor}' no está declarado como función", t, Categoria.SIMBOLO)
        return Variable(t.valor)

    def argumentos(self, simbolo: Token, aridad: int) -> tuple:
        if self.actual.tipo != PAR_IZQ:
            self.error(f"'{simbolo.valor}' tiene aridad {aridad} y requiere {aridad} argumento(s) entre paréntesis",
                       simbolo, Categoria.ARIDAD)
        self.avanzar()
        args = [self.termino()]
        while self.actual.tipo == COMA:
            self.avanzar()
            args.append(self.termino())
        self.esperar(PAR_DER, f"Falta ')' para cerrar los argumentos de '{simbolo.valor}'")
        if len(args) != aridad:
            self.error(f"'{simbolo.valor}' tiene aridad {aridad} pero recibió {len(args)} argumento(s)",
                       simbolo, Categoria.ARIDAD)
        return tuple(args)
