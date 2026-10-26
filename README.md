# Evaluador semántico · MM3032 Lógica Matemática (UVG)

Aplicación web que decide si una fórmula de primer orden es **Verdadera** o **Falsa** en una interpretación finita y explica las razones decisivas.

**Equipo:** David Lopez · Carlos Lopez · Natanael

## Cómo ejecutarla

**Con Docker** (requiere Docker Desktop encendido):

```bash
docker compose up -d --build
# abrir http://localhost:8765
# usar otro puerto:  PUERTO=9000 docker compose up -d   (PowerShell: $env:PUERTO=9000; docker compose up -d)
```

**Sin Docker** (Python 3.10 o superior):

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install flask
python app.py                   # http://localhost:8765
```

**Pruebas:** `python -m unittest -v tests.test_evaluador`

## Estructura

| Archivo | Responsabilidad | Requisito |
|---|---|---|
| `evaluador/lenguaje.py` | Símbolos funcionales (aridad 0 = constante) y predicados (aridad ≥ 1) | 1 |
| `evaluador/interpretacion.py` | Dominio no vacío, funciones totales, relaciones no vacías, entorno σ | 2, 4, 7 |
| `evaluador/sintaxis.py` | Lexer, parser y AST; variables libres | 3, 4, 7 |
| `evaluador/semantica.py` | Evaluación con árbol de justificación | 6 |
| `evaluador/errores.py` | Categorías de error: sintaxis, símbolo, aridad, dominio, tupla, asignación | 7 |
| `app.py` | API Flask (`/api/analizar`, `/api/evaluar`) | 5 |
| `web/` | Interfaz: HTML, CSS y JS sin frameworks | 5 |

## Sintaxis aceptada

```
φ ::= P(t1, ..., tn) | t1 = t2 | ¬φ | (φ ∧ ψ) | (φ ∨ ψ) | (φ → ψ) | ∀x φ | ∃x φ
t ::= x | c | f(t1, ..., tn)
```

- Los paréntesis son símbolos lógicos: **toda fórmula binaria va entre paréntesis** y no se aceptan paréntesis sobrantes.
- Todo identificador que no se haya declarado como símbolo es una variable.
- Formas desde el teclado: `~ !` → ¬, `& /\` → ∧, `| \/` → ∨, `-> =>` → →, `forall` → ∀, `exists` → ∃.

## Semántica de los cuantificadores

`∀x φ` y `∃x φ` se evalúan como un ciclo `for d in 𝒟` con `x ↦ d`:

| Caso | Se detiene cuando… | Justificación |
|---|---|---|
| ∀ falso | aparece la primera instancia falsa | contraejemplo |
| ∀ verdadero | recorre todo 𝒟 | comprobación completa |
| ∃ verdadero | aparece la primera instancia verdadera | testigo |
| ∃ falso | recorre todo 𝒟 | comprobación completa |

La interfaz anima ese recorrido. Se puede reproducir, avanzar paso a paso y hacer clic en cada instancia para ver su subárbol.
