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

## Batalla Lógica

Abre `http://localhost:8765/juego` o pulsa **Batalla Lógica** en el evaluador.
El enlace **← Evaluador** permite volver a la aplicación original.

1. Selecciona un soldado de tu equipo y pulsa **Preparar ataque**.
2. Elige el soldado objetivo en el selector.
3. Escribe una **fórmula cerrada**, revisa la previsualización y ejecuta el ataque.

`objetivo` y `yo` son constantes de aridad cero: nombran al objetivo elegido y al
atacante. Por ejemplo, `(Enemigo(objetivo) ∧ Arquero(objetivo))` permite atacar al
objetivo cuando es un arquero enemigo. `∃y (Mio(y) ∧ Cerca(objetivo,y))` comprueba
si tiene algún vecino de tu equipo. Las variables `y` y `z` deben quedar ligadas
por un cuantificador; `Enemigo(x)` y `Cerca(objetivo,y)` se rechazan por tener
variables libres. No se completa la fórmula mediante asignaciones implícitas.

En **Todos** y en el tutorial se realiza una comprobación independiente por soldado:
la interpretación de la constante `objetivo` nombra al soldado de esa comprobación.
La fórmula sigue cerrada en todas esas interpretaciones. Solo reciben el efecto
los soldados seleccionados cuya comprobación es verdadera y que están en alcance.
El tutorial conserva sus nueve lecciones, con ejemplos, pistas y soluciones cerradas.

Pruebas del proyecto completo dentro de Docker desde PowerShell:

```powershell
docker compose run --rm --no-deps --volume "${PWD}/tests:/app/tests:ro" evaluador python -m unittest discover -s tests
```

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
