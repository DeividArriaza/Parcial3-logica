"""Servidor web del evaluador semántico (Req. 5).

Toda la lógica vive en el paquete `evaluador`; aquí solo se traduce JSON ↔ objetos.
Ejecutar sin Docker:  python app.py   →  http://localhost:8765  (otro puerto: variable PUERTO)
"""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from evaluador import ErrorValidacion, Interpretacion, Lenguaje, analizar, variables_libres
from evaluador.semantica import Evaluador
from evaluador.errores import Categoria
from evaluador.juego import crear_estado, mover, previsualizar, atacar, terminar_turno, niveles
from evaluador.juego import practicar

ESTATICOS = Path(__file__).parent / "web"
app = Flask(__name__, static_folder=str(ESTATICOS), static_url_path="/static")


class PeticionInvalida(Exception):
    pass


def _errores(origen: str, e: ErrorValidacion) -> list[dict]:
    return [{"origen": origen, "categoria": p.categoria.value, "mensaje": p.mensaje, "posicion": p.posicion}
            for p in e.problemas]


def _lenguaje(datos: dict) -> Lenguaje:
    try:
        return Lenguaje(datos["lenguaje"]["funciones"], datos["lenguaje"]["predicados"])
    except (KeyError, TypeError, AttributeError):
        raise PeticionInvalida("Falta la declaración del lenguaje")


def _interpretacion(datos: dict, lenguaje: Lenguaje) -> Interpretacion:
    try:
        funciones = {
            f: {tuple(args): valor for args, valor in filas} for f, filas in datos["funciones"].items()
        }
        relaciones = {p: {tuple(t) for t in tuplas} for p, tuplas in datos["relaciones"].items()}
        dominio = list(datos["dominio"])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise PeticionInvalida("La interpretación no tiene el formato esperado")
    return Interpretacion(lenguaje, dominio, funciones, relaciones)


@app.errorhandler(PeticionInvalida)
def _peticion_invalida(e):
    return jsonify(ok=False, errores=[{"origen": "peticion", "categoria": "sintaxis", "mensaje": str(e),
                                       "posicion": None}]), 400


@app.get("/")
def inicio():
    return send_from_directory(ESTATICOS, "index.html")


def _respuesta_juego(funcion, *args):
    """Traduce errores de entrada y de recursión a respuestas controladas del juego."""
    try:
        return jsonify(funcion(*args))
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("juego", e))
    except RecursionError:
        error = ErrorValidacion.uno(Categoria.SINTAXIS, "La fórmula o el cuerpo tienen demasiada anidación")
        return jsonify(ok=False, errores=_errores("juego", error))
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as e:
        error = ErrorValidacion.uno(Categoria.DOMINIO, f"Solicitud de juego inválida: {e}")
        return jsonify(ok=False, errores=_errores("juego", error))


def _error_cuerpo_juego(mensaje):
    """Devuelve un error de petición con la estructura pública del evaluador."""
    error = ErrorValidacion.uno(Categoria.SINTAXIS, mensaje)
    return jsonify(ok=False, errores=_errores("peticion", error)), 400


def _cuerpo_juego():
    """Exige un objeto JSON y controla la anidación excesiva del cuerpo."""
    try:
        datos = request.get_json(silent=True)
    except RecursionError:
        return None, _error_cuerpo_juego("El cuerpo JSON tiene demasiada anidación")
    if not isinstance(datos, dict):
        return None, _error_cuerpo_juego("El cuerpo JSON debe ser un objeto")
    return datos, None


def _campo_juego(datos, nombre, tipo, requerido=True, defecto=None):
    """Valida un campo antes de entregarlo al motor."""
    if nombre not in datos:
        if requerido:
            raise ErrorValidacion.uno(Categoria.SINTAXIS, f"Falta el campo '{nombre}'")
        return defecto
    valor = datos[nombre]
    valido = isinstance(valor, tipo)
    if tipo is int:
        valido = type(valor) is int
    if not valido:
        esperado = " o ".join(t.__name__ for t in (tipo if isinstance(tipo, tuple) else (tipo,)))
        raise ErrorValidacion.uno(Categoria.SINTAXIS, f"El campo '{nombre}' debe ser de tipo {esperado}")
    return valor


@app.get("/juego")
def pagina_juego():
    """Sirve la página del juego."""
    return send_from_directory(ESTATICOS, "juego.html")


@app.get("/api/juego/niveles")
def api_juego_niveles():
    """Entrega las nueve lecciones y sus pasos guiados."""
    return jsonify(ok=True, niveles=niveles())


@app.post("/api/juego/nueva")
def api_juego_nueva():
    """Crea una partida a partir de los parámetros de la petición."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        modo = _campo_juego(datos, "modo", str, requerido=False, defecto="cpu")
        dificultad = _campo_juego(datos, "dificultad", dict, requerido=False)
        nivel = _campo_juego(datos, "nivel", int, requerido=False)
        semilla = _campo_juego(datos, "semilla", int, requerido=False)
        paso = _campo_juego(datos, "paso", int, requerido=False)
        return jsonify(ok=True, estado=crear_estado(modo, dificultad, nivel, semilla, paso))
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("juego", e))


@app.post("/api/juego/mover")
def api_juego_mover():
    """Valida el destino y ejecuta un movimiento."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        estado = _campo_juego(datos, "estado", dict)
        unidad = _campo_juego(datos, "unidad", str)
        destino = _campo_juego(datos, "destino", list)
        if len(destino) != 2 or any(type(v) is not int for v in destino):
            return _error_cuerpo_juego("El campo 'destino' debe ser [columna, fila] con enteros")
        return _respuesta_juego(mover, estado, unidad, destino)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("peticion", e)), 400


@app.post("/api/juego/previsualizar")
def api_juego_previsualizar():
    """Muestra el resultado previsto y la lectura de la fórmula."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        estado = _campo_juego(datos, "estado", dict)
        atacante = _campo_juego(datos, "atacante", str)
        formula = _campo_juego(datos, "formula", str, requerido=False, defecto="")
        return _respuesta_juego(previsualizar, estado, atacante, formula)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("peticion", e)), 400


@app.post("/api/juego/atacar")
def api_juego_atacar():
    """Ejecuta el ataque y devuelve efectos y retroalimentación."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        estado = _campo_juego(datos, "estado", dict)
        atacante = _campo_juego(datos, "atacante", str)
        formula = _campo_juego(datos, "formula", str, requerido=False, defecto="")
        return _respuesta_juego(atacar, estado, atacante, formula)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("peticion", e)), 400


@app.post("/api/juego/terminar_turno")
def api_juego_terminar_turno():
    """Pasa el turno y ejecuta las acciones de la CPU si corresponde."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        estado = _campo_juego(datos, "estado", dict)
        return _respuesta_juego(terminar_turno, estado)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("peticion", e)), 400


@app.post("/api/juego/practicar")
def api_juego_practicar():
    """Comprueba una fórmula guiada sin consumir energía ni modificar la partida."""
    datos, error = _cuerpo_juego()
    if error:
        return error
    try:
        estado = _campo_juego(datos, "estado", dict)
        nivel = _campo_juego(datos, "nivel", int)
        paso = _campo_juego(datos, "paso", int)
        formula = _campo_juego(datos, "formula", str)
        return _respuesta_juego(practicar, estado, nivel, paso, formula)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("peticion", e)), 400


@app.post("/api/analizar")
def api_analizar():
    """Análisis sintáctico en vivo: devuelve las variables libres para pedir el entorno."""
    datos = request.get_json(force=True, silent=True) or {}
    try:
        lenguaje = _lenguaje(datos)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("lenguaje", e))
    try:
        formula = analizar(datos.get("formula", ""), lenguaje)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("formula", e))
    return jsonify(ok=True, formula=str(formula), libres=variables_libres(formula))


@app.post("/api/evaluar")
def api_evaluar():
    datos = request.get_json(force=True, silent=True) or {}
    try:
        lenguaje = _lenguaje(datos)
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("lenguaje", e))

    # Se reúnen los errores de la fórmula y de la interpretación juntos (Req. 7).
    errores, formula, interpretacion = [], None, None
    try:
        formula = analizar(datos.get("formula", ""), lenguaje)
    except ErrorValidacion as e:
        errores += _errores("formula", e)
    try:
        interpretacion = _interpretacion(datos, lenguaje)
    except ErrorValidacion as e:
        errores += _errores("interpretacion", e)
    if errores:
        return jsonify(ok=False, errores=errores)

    libres = variables_libres(formula)
    try:
        entorno = interpretacion.validar_entorno(libres, datos.get("entorno") or {})
    except ErrorValidacion as e:
        return jsonify(ok=False, errores=_errores("entorno", e))

    arbol = Evaluador(interpretacion).evaluar(formula, entorno)
    return jsonify(ok=True, valor=arbol.valor, formula=str(formula), libres=libres, entorno=entorno,
                   dominio=interpretacion.dominio, arbol=arbol.como_dict())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PUERTO", 8765)), debug=os.environ.get("DEBUG") == "1")
