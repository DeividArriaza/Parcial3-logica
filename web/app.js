// Interfaz del evaluador semántico. La validación y la evaluación ocurren en el
// servidor (paquete `evaluador`); este archivo solo arma la entrada y dibuja el resultado.
"use strict";

const MAX_TUPLAS = 400;          // límite de filas a dibujar por símbolo
const MS_POR_PASO = 900;         // velocidad de la animación del recorrido
const SIN_ANIMACION = matchMedia("(prefers-reduced-motion: reduce)").matches;

const $ = (sel) => document.querySelector(sel);
const clave = (tupla) => JSON.stringify(tupla);

// ------------------------------------------------------------------ estado

let siguienteId = 1;
const estado = {
  simbolos: [],       // {id, nombre, tipo: "funcion" | "predicado", aridad}
  funciones: {},      // id -> {claveTupla: valor}
  relaciones: {},     // id -> Set(claveTupla)
  entorno: {},        // variable -> elemento
  libres: [],
};

function nuevoSimbolo(nombre = "", tipo = "predicado", aridad = 1) {
  const s = { id: siguienteId++, nombre, tipo, aridad };
  estado.simbolos.push(s);
  estado.funciones[s.id] = {};
  estado.relaciones[s.id] = new Set();
  return s;
}

// Texto del dominio tal como se enviará al servidor (puede traer errores que el servidor reporta).
function dominioCrudo() {
  const texto = $("#dominio").value.replace(/[{}]/g, "").trim();
  return texto === "" ? [] : texto.split(",").map((e) => e.trim());
}

// Elementos utilizables para dibujar tablas: sin vacíos ni repetidos.
function dominio() {
  return [...new Set(dominioCrudo().filter((e) => e !== "" && !/[(),\s]/.test(e)))];
}

function tuplas(D, n) {
  let res = [[]];
  for (let i = 0; i < n; i++) res = res.flatMap((t) => D.map((d) => [...t, d]));
  return res;
}

// ------------------------------------------------------------------ 1. lenguaje

function dibujarSimbolos() {
  const cuerpo = $("#tabla-simbolos");
  cuerpo.innerHTML = "";
  for (const s of estado.simbolos) {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td><input type="text" id="sim-nombre-${s.id}" value="${escapar(s.nombre)}" aria-label="Nombre" spellcheck="false"></td>
      <td><select id="sim-tipo-${s.id}" aria-label="Tipo">
            <option value="funcion"${s.tipo === "funcion" ? " selected" : ""}>función</option>
            <option value="predicado"${s.tipo === "predicado" ? " selected" : ""}>predicado</option>
          </select></td>
      <td><input type="number" id="sim-aridad-${s.id}" value="${s.aridad}" min="0" max="6" aria-label="Aridad"></td>
      <td><button class="quitar" title="Quitar símbolo" aria-label="Quitar ${escapar(s.nombre)}">✕</button></td>`;
    fila.querySelector("input[type=text]").addEventListener("input", (e) => { s.nombre = e.target.value.trim(); cambioLenguaje(); });
    fila.querySelector("select").addEventListener("change", (e) => { s.tipo = e.target.value; cambioLenguaje(); });
    fila.querySelector("input[type=number]").addEventListener("input", (e) => {
      s.aridad = e.target.value === "" ? "" : Number(e.target.value);
      cambioLenguaje();
    });
    fila.querySelector(".quitar").addEventListener("click", () => {
      estado.simbolos = estado.simbolos.filter((o) => o !== s);
      dibujarSimbolos();
      cambioLenguaje();
    });
    cuerpo.appendChild(fila);
  }
}

function cambioLenguaje() {
  dibujarTablas();
  analizarPronto();
}

// ------------------------------------------------------------------ 2. interpretación

function dibujarTablas() {
  const cont = $("#tablas");
  cont.innerHTML = "";
  const D = dominio();
  if (D.length === 0) {
    cont.innerHTML = `<p class="aviso">Ingrese el dominio para completar las funciones y relaciones.</p>`;
    return;
  }
  for (const s of estado.simbolos) {
    if (!s.nombre || !Number.isInteger(s.aridad) || s.aridad < 0) continue;
    const bloque = document.createElement("div");
    bloque.className = "simbolo";
    const firma = s.tipo === "funcion"
      ? (s.aridad === 0 ? "constante" : `función 𝒟${sup(s.aridad)} → 𝒟`)
      : `relación ⊆ 𝒟${sup(s.aridad)}`;
    bloque.innerHTML = `<h3>${escapar(s.nombre)}ᴵ <small>${firma}</small></h3>`;
    const n = Math.pow(D.length, s.aridad);
    if (n > MAX_TUPLAS) {
      bloque.insertAdjacentHTML("beforeend", `<p class="aviso">Son ${n} tuplas; reduzca el dominio o la aridad para poder editarlas.</p>`);
    } else if (s.tipo === "funcion") {
      bloque.appendChild(s.aridad === 2 ? matrizFuncion(s, D) : filasFuncion(s, D));
    } else if (s.aridad === 0) {
      bloque.insertAdjacentHTML("beforeend", `<p class="aviso">Los predicados deben tener aridad ≥ 1.</p>`);
    } else {
      bloque.appendChild(s.aridad === 2 ? matrizRelacion(s, D) : filasRelacion(s, D));
    }
    cont.appendChild(bloque);
  }
}

function selectorValor(s, tupla, D) {
  const tabla = estado.funciones[s.id];
  const actual = tabla[clave(tupla)];
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", `${s.nombre}(${tupla.join(", ")})`);
  sel.innerHTML = `<option value="">—</option>` +
    D.map((d) => `<option${d === actual ? " selected" : ""}>${escapar(d)}</option>`).join("");
  sel.addEventListener("change", () => {
    if (sel.value === "") delete tabla[clave(tupla)]; else tabla[clave(tupla)] = sel.value;
  });
  return sel;
}

function filasFuncion(s, D) {
  const cont = document.createElement("div");
  cont.className = "filas";
  for (const t of tuplas(D, s.aridad)) {
    const etiqueta = document.createElement("label");
    etiqueta.textContent = (s.aridad === 0 ? s.nombre : `${s.nombre}(${t.join(", ")})`) + " =";
    etiqueta.appendChild(selectorValor(s, t, D));
    cont.appendChild(etiqueta);
  }
  return cont;
}

function matrizFuncion(s, D) {
  return matriz(s, D, (t) => selectorValor(s, t, D));
}

function casilla(s, tupla) {
  const rel = estado.relaciones[s.id];
  const caja = document.createElement("input");
  caja.type = "checkbox";
  caja.checked = rel.has(clave(tupla));
  caja.setAttribute("aria-label", `(${tupla.join(", ")}) ∈ ${s.nombre}`);
  caja.addEventListener("change", () => caja.checked ? rel.add(clave(tupla)) : rel.delete(clave(tupla)));
  return caja;
}

function filasRelacion(s, D) {
  const cont = document.createElement("div");
  cont.className = "filas";
  for (const t of tuplas(D, s.aridad)) {
    const etiqueta = document.createElement("label");
    etiqueta.className = "toggle";
    etiqueta.appendChild(casilla(s, t));
    etiqueta.append(t.length === 1 ? t[0] : `(${t.join(", ")})`);
    cont.appendChild(etiqueta);
  }
  return cont;
}

function matrizRelacion(s, D) {
  return matriz(s, D, (t) => casilla(s, t));
}

// Tabla de doble entrada: filas = primer argumento, columnas = segundo.
function matriz(s, D, celda) {
  const envoltura = document.createElement("div");
  envoltura.className = "matriz-scroll";
  const tabla = document.createElement("table");
  tabla.className = "matriz";
  const cab = tabla.insertRow();
  cab.innerHTML = `<th class="esq">${escapar(s.nombre)}</th>` + D.map((d) => `<th>${escapar(d)}</th>`).join("");
  for (const a of D) {
    const fila = tabla.insertRow();
    fila.innerHTML = `<th>${escapar(a)}</th>`;
    for (const b of D) fila.insertCell().appendChild(celda([a, b]));
  }
  envoltura.appendChild(tabla);
  return envoltura;
}

// ------------------------------------------------------------------ 3. fórmula y entorno

const REEMPLAZOS = [["->", "→"], ["=>", "→"], ["/\\", "∧"], ["\\/", "∨"], ["~", "¬"], ["!", "¬"], ["&", "∧"], ["|", "∨"]];

// Convierte las formas de teclado a símbolos lógicos sin mover el cursor de lugar.
function normalizarEscritura() {
  const campo = $("#formula");
  let texto = campo.value;
  let cursor = campo.selectionStart;
  for (const [de, a] of REEMPLAZOS) {
    let i;
    while ((i = texto.indexOf(de)) !== -1) {
      texto = texto.slice(0, i) + a + texto.slice(i + de.length);
      if (cursor > i) cursor -= Math.min(de.length - a.length, cursor - i);
    }
  }
  if (texto !== campo.value) {
    campo.value = texto;
    campo.setSelectionRange(cursor, cursor);
  }
}

function insertar(texto) {
  const campo = $("#formula");
  const ini = campo.selectionStart ?? campo.value.length;
  const fin = campo.selectionEnd ?? campo.value.length;
  campo.value = campo.value.slice(0, ini) + texto + campo.value.slice(fin);
  campo.focus();
  campo.setSelectionRange(ini + texto.length, ini + texto.length);
  analizarPronto();
}

function borrarUno() {
  const campo = $("#formula");
  const ini = campo.selectionStart, fin = campo.selectionEnd;
  if (ini !== fin) campo.value = campo.value.slice(0, ini) + campo.value.slice(fin);
  else if (ini > 0) campo.value = campo.value.slice(0, ini - 1) + campo.value.slice(ini);
  const pos = ini !== fin ? ini : Math.max(0, ini - 1);
  campo.focus();
  campo.setSelectionRange(pos, pos);
  analizarPronto();
}

function declaracion() {
  const funciones = {}, predicados = {};
  for (const s of estado.simbolos) (s.tipo === "funcion" ? funciones : predicados)[s.nombre] = s.aridad;
  return { funciones, predicados };
}

// Errores del lenguaje que solo se ven antes de armar el JSON (nombres repetidos o vacíos).
function erroresLocalesLenguaje() {
  const errores = [];
  const vistos = new Set();
  for (const s of estado.simbolos) {
    if (!s.nombre) errores.push({ categoria: "lenguaje", mensaje: "Hay un símbolo sin nombre" });
    else if (vistos.has(s.nombre)) errores.push({ categoria: "lenguaje", mensaje: `El símbolo '${s.nombre}' está declarado dos veces` });
    vistos.add(s.nombre);
  }
  return errores;
}

let temporizador = null;
function analizarPronto() {
  clearTimeout(temporizador);
  temporizador = setTimeout(analizar, 250);
}

async function analizar() {
  const caja = $("#estado-formula");
  const texto = $("#formula").value;
  if (!texto.trim()) {
    caja.className = "estado";
    caja.textContent = "";
    estado.libres = [];
    dibujarEntorno();
    return;
  }
  if (erroresLocalesLenguaje().length) return;
  const r = await pedir("/api/analizar", { lenguaje: declaracion(), formula: texto });
  if (!r) return;
  if (r.ok) {
    caja.className = "estado ok";
    caja.textContent = r.libres.length
      ? `✓ Bien formada · fórmula abierta, variables libres: ${r.libres.join(", ")}`
      : "✓ Bien formada · fórmula cerrada (no requiere entorno)";
    $("#formula").classList.remove("invalido");
    estado.libres = r.libres;
  } else {
    const e = r.errores[0];
    caja.className = "estado mal";
    caja.textContent = `✗ ${e.mensaje}`;
    $("#formula").classList.add("invalido");
    estado.libres = [];
  }
  dibujarEntorno();
}

function dibujarEntorno() {
  const cont = $("#entorno");
  cont.innerHTML = "";
  if (!estado.libres.length) return;
  const D = dominio();
  cont.insertAdjacentHTML("beforeend", `<span class="etiqueta">Entorno σ</span>`);
  for (const x of estado.libres) {
    const etiqueta = document.createElement("label");
    etiqueta.textContent = `σ(${x}) =`;
    const sel = document.createElement("select");
    sel.id = `entorno-${x}`;
    sel.innerHTML = `<option value="">—</option>` +
      D.map((d) => `<option${estado.entorno[x] === d ? " selected" : ""}>${escapar(d)}</option>`).join("");
    sel.addEventListener("change", () => { estado.entorno[x] = sel.value; });
    etiqueta.appendChild(sel);
    cont.appendChild(etiqueta);
  }
}

// ------------------------------------------------------------------ evaluación

function peticionCompleta() {
  const D = dominio();
  const enD = (t) => t.every((e) => D.includes(e));
  const funciones = {}, relaciones = {};
  for (const s of estado.simbolos) {
    if (s.tipo === "funcion") {
      funciones[s.nombre] = Object.entries(estado.funciones[s.id])
        .map(([k, v]) => [JSON.parse(k), v])
        .filter(([t, v]) => t.length === s.aridad && enD(t) && D.includes(v));
    } else {
      relaciones[s.nombre] = [...estado.relaciones[s.id]].map((k) => JSON.parse(k))
        .filter((t) => t.length === s.aridad && enD(t));
    }
  }
  const entorno = {};
  for (const x of estado.libres) if (estado.entorno[x]) entorno[x] = estado.entorno[x];
  return { lenguaje: declaracion(), dominio: dominioCrudo(), funciones, relaciones, formula: $("#formula").value, entorno };
}

async function evaluar() {
  for (const id of ["#err-lenguaje", "#err-interpretacion", "#err-formula"]) $(id).innerHTML = "";
  const locales = erroresLocalesLenguaje();
  if (locales.length) {
    mostrarErrores(locales.map((e) => ({ ...e, origen: "lenguaje" })));
    return;
  }
  const r = await pedir("/api/evaluar", peticionCompleta());
  if (!r) return;
  if (!r.ok) mostrarErrores(r.errores);
  else dibujarResultado(r);
}

function mostrarErrores(errores) {
  const destino = { lenguaje: "#err-lenguaje", interpretacion: "#err-interpretacion", formula: "#err-formula", entorno: "#err-formula" };
  const formula = $("#formula").value;
  for (const e of errores) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="cat">${escapar(e.categoria)}</span>${escapar(e.mensaje)}`;
    if (e.origen === "formula" && e.posicion !== null && e.posicion !== undefined) {
      const pre = document.createElement("pre");
      pre.textContent = `${formula}\n${" ".repeat(e.posicion)}^`;
      li.appendChild(pre);
    }
    $(destino[e.origen] || "#err-formula").appendChild(li);
  }
  $("#resultado").innerHTML = `
    <div class="veredicto"><span class="pildora N">Sin valor de verdad</span></div>
    <p class="resumen">Hay ${errores.length} error(es) en la entrada. Corríjalos para poder evaluar la fórmula.</p>`;
}

// ------------------------------------------------------------------ resultado y recorrido

function dibujarResultado(r) {
  detenerAnimaciones();
  const cont = $("#resultado");
  const valor = r.valor ? "V" : "F";
  const sigma = Object.keys(r.entorno).length
    ? ` con σ = {${Object.entries(r.entorno).map(([x, d]) => `${x} ↦ ${d}`).join(", ")}}` : "";
  cont.innerHTML = `
    <div class="veredicto"><span class="pildora ${valor}">${r.valor ? "Verdadero" : "Falso"}</span></div>
    <p class="resumen"><code>${escapar(r.formula)}</code> es ${r.valor ? "verdadera" : "falsa"} en la interpretación ℐ${escapar(sigma)}.</p>`;
  const arbol = document.createElement("div");
  arbol.className = "arbol";
  arbol.appendChild(nodo(r.arbol, r.dominio, r.entorno, true));
  cont.appendChild(arbol);
}

const ES_CUANTIFICADOR = new Set(["testigo", "contraejemplo", "comprobacion"]);

function nodo(paso, D, contexto, raiz) {
  const div = document.createElement("div");
  div.className = `nodo ${paso.valor ? "V" : "F"}`;
  const ctx = Object.keys(contexto).length
    ? `σ = {${Object.entries(contexto).map(([x, d]) => `${x} ↦ ${d}`).join(", ")}}` : "";
  div.innerHTML = `
    <div class="cab"><span class="chip ${paso.valor ? "V" : "F"}">${paso.valor ? "V" : "F"}</span>
      <code>${escapar(paso.formula)}</code>${ctx ? `<span class="ctx">${escapar(ctx)}</span>` : ""}</div>
    <div class="exp">${escapar(paso.explicacion)}</div>`;
  if (ES_CUANTIFICADOR.has(paso.tipo)) div.appendChild(recorrido(paso, D, contexto, raiz));
  else for (const h of paso.hijos) div.appendChild(nodo(h, D, contexto, false));
  return div;
}

const animaciones = new Set();
function detenerAnimaciones() {
  for (const a of animaciones) clearInterval(a);
  animaciones.clear();
}

// Muestra el cuantificador como un ciclo `for d in 𝒟` que se detiene en la instancia decisiva.
function recorrido(paso, D, contexto, animar) {
  const esPara = paso.formula.startsWith("∀");
  const variable = paso.hijos[0].asignacion.split(" ↦ ")[0];
  const visitados = paso.hijos.length;
  const decisivo = paso.tipo === "comprobacion" ? -1 : visitados - 1;
  const cuerpoTexto = paso.formula.replace(/^[∀∃]\S+\s*/, "");

  const caja = document.createElement("div");
  caja.className = "recorrido";
  caja.innerHTML = `
    <div class="ciclo">
      <span class="lazo">for ${escapar(variable)} in 𝒟:  ${esPara ? "si es falsa → break" : "si es verdadera → break"}</span>
      <button data-a="inicio" title="Reiniciar">⏮</button>
      <button data-a="play" title="Reproducir">▶</button>
      <button data-a="sig" title="Siguiente paso">⏭</button>
    </div>
    <div class="pistas"></div>
    <div class="mensaje"></div>
    <div class="detalle"></div>`;
  const pistas = caja.querySelector(".pistas");
  const mensaje = caja.querySelector(".mensaje");
  const detalle = caja.querySelector(".detalle");
  const botonPlay = caja.querySelector('[data-a="play"]');

  let revelados = animar && !SIN_ANIMACION ? 0 : visitados;
  let seleccion = revelados ? (decisivo >= 0 ? decisivo : visitados - 1) : -1;
  let reloj = null;

  function pintar() {
    pistas.innerHTML = "";
    D.forEach((d, i) => {
      const b = document.createElement("button");
      b.textContent = `${variable} ↦ ${d}`;
      if (i >= visitados) {
        b.className = revelados === visitados ? "paso omitido" : "paso pendiente";
        b.title = "No se evalúa: el ciclo terminó antes";
        b.disabled = true;
      } else if (i >= revelados) {
        b.className = "paso pendiente";
        b.disabled = true;
      } else {
        const h = paso.hijos[i];
        b.className = `paso ${h.valor ? "V" : "F"}${i === decisivo ? " decisivo" : ""}${i === seleccion ? " sel" : ""}`;
        b.textContent += h.valor ? "  V" : "  F";
        b.addEventListener("click", () => { pausar(); seleccion = i; pintar(); });
      }
      pistas.appendChild(b);
    });

    mensaje.className = "mensaje";
    if (seleccion < 0) {
      mensaje.textContent = `Se recorrerá 𝒟 = {${D.join(", ")}} evaluando ${cuerpoTexto}…`;
    } else {
      const h = paso.hijos[seleccion];
      const d = h.asignacion.split(" ↦ ")[1];
      let texto = `${variable} ↦ ${d}: ${cuerpoTexto} es ${h.valor ? "verdadera" : "falsa"}`;
      if (seleccion === decisivo) {
        texto += esPara
          ? ` → contraejemplo encontrado; el ∀ es Falso y el ciclo se detiene.`
          : ` → testigo encontrado; el ∃ es Verdadero y el ciclo se detiene.`;
        mensaje.className = "mensaje final";
      } else if (revelados === visitados && seleccion === visitados - 1 && decisivo < 0) {
        texto += esPara
          ? `. Se recorrió todo 𝒟 sin hallar un falso: el ∀ es Verdadero.`
          : `. Se recorrió todo 𝒟 sin hallar un verdadero: el ∃ es Falso.`;
        mensaje.className = "mensaje final";
      } else {
        texto += " → se continúa con el siguiente elemento.";
      }
      mensaje.textContent = texto;
    }

    detalle.innerHTML = "";
    if (seleccion >= 0) {
      const h = paso.hijos[seleccion];
      const d = h.asignacion.split(" ↦ ")[1];
      detalle.appendChild(nodo(h, D, { ...contexto, [variable]: d }, false));
    }
    botonPlay.textContent = reloj ? "⏸" : "▶";
  }

  function avanzar() {
    if (revelados >= visitados) { pausar(); return; }
    revelados++;
    seleccion = revelados - 1;
    if (revelados >= visitados) pausar();
    pintar();
  }
  function reproducir() {
    if (revelados >= visitados) { revelados = 0; seleccion = -1; }
    reloj = setInterval(avanzar, MS_POR_PASO);
    animaciones.add(reloj);
    pintar();
  }
  function pausar() {
    if (reloj) { clearInterval(reloj); animaciones.delete(reloj); reloj = null; }
  }

  caja.querySelector('[data-a="inicio"]').addEventListener("click", () => { pausar(); revelados = 0; seleccion = -1; pintar(); });
  caja.querySelector('[data-a="sig"]').addEventListener("click", () => { pausar(); avanzar(); });
  botonPlay.addEventListener("click", () => (reloj ? (pausar(), pintar()) : reproducir()));

  pintar();
  if (revelados === 0) reproducir();
  return caja;
}

// ------------------------------------------------------------------ utilidades

async function pedir(url, cuerpo) {
  try {
    const resp = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    return await resp.json();
  } catch {
    $("#resultado").innerHTML = `<p class="vacio">No se pudo contactar al servidor. Verifique que la aplicación siga en ejecución.</p>`;
    return null;
  }
}

function escapar(t) {
  return String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function sup(n) {
  return String(n).replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]);
}

// ------------------------------------------------------------------ ejemplo e inicio

function cargarEjemplo() {
  estado.simbolos = [];
  estado.entorno = {};
  const c = nuevoSimbolo("c", "funcion", 0);
  const s = nuevoSimbolo("s", "funcion", 1);
  const P = nuevoSimbolo("P", "predicado", 1);
  const R = nuevoSimbolo("R", "predicado", 2);
  $("#dominio").value = "0, 1, 2";
  estado.funciones[c.id] = { [clave([])]: "0" };
  estado.funciones[s.id] = { [clave(["0"])]: "1", [clave(["1"])]: "2", [clave(["2"])]: "0" };   // sucesor módulo 3
  estado.relaciones[P.id] = new Set([clave(["0"]), clave(["2"])]);                               // "es par"
  estado.relaciones[R.id] = new Set([clave(["0", "1"]), clave(["0", "2"]), clave(["1", "2"])]); // "menor que"
  $("#formula").value = "∀x (P(x) → ∃y R(x, y))";
  reiniciarVista();
}

function limpiar() {
  estado.simbolos = [];
  estado.entorno = {};
  $("#dominio").value = "";
  $("#formula").value = "";
  nuevoSimbolo();
  reiniciarVista();
}

function reiniciarVista() {
  detenerAnimaciones();
  for (const id of ["#err-lenguaje", "#err-interpretacion", "#err-formula"]) $(id).innerHTML = "";
  $("#resultado").innerHTML = `<p class="vacio">Cuando evalúe una fórmula verá aquí si es Verdadera o Falsa y el árbol con las razones decisivas.</p>`;
  dibujarSimbolos();
  dibujarTablas();
  analizar();
}

$("#btn-agregar-simbolo").addEventListener("click", () => { nuevoSimbolo(); dibujarSimbolos(); cambioLenguaje(); });
$("#btn-ejemplo").addEventListener("click", cargarEjemplo);
$("#btn-limpiar").addEventListener("click", limpiar);
$("#btn-evaluar").addEventListener("click", evaluar);
$("#dominio").addEventListener("input", () => { dibujarTablas(); dibujarEntorno(); });
$("#formula").addEventListener("input", () => { normalizarEscritura(); analizarPronto(); });
$("#formula").addEventListener("keydown", (e) => { if (e.key === "Enter") evaluar(); });
$("#teclado").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.accion === "borrar") borrarUno(); else insertar(b.dataset.ins);
});

cargarEjemplo();
