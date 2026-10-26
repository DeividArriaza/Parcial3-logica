"""Servidor web del evaluador semántico (Req. 5).

Toda la lógica vive en el paquete `evaluador`; aquí solo se traduce JSON ↔ objetos.
Ejecutar sin Docker:  python app.py   →  http://localhost:8765  (otro puerto: variable PUERTO)
"""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from evaluador import ErrorValidacion, Interpretacion, Lenguaje, analizar, variables_libres
from evaluador.semantica import Evaluador

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
        funciones = {f: {tuple(args): valor for args, valor in filas} for f, filas in datos["funciones"].items()}
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
