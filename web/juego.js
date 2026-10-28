"use strict";

(() => {
  // ------------------------ Estado de la interfaz y datos de presentación
  const $ = (id) => document.getElementById(id);
  const arte = window.ArteBatalla;
  const lienzo = $("tablero");
  const contexto = lienzo.getContext("2d");
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)");
  const TAM = 80;
  let estado = null;
  let seleccionado = null;
  let modo = "tutorial";
  let niveles = [];
  let ocupado = false;
  let previsualizacion = null;
  let secuenciaPrevisualizacion = 0;
  let temporizadorPrevisualizacion;
  let editorAbierto = false;
  let fotograma = 0;
  let celdaCursor = null;
  let animaciones = [];
  let configuracionAnterior = null;
  let cargandoNiveles = false;
  const instructor = new window.InstructorBatalla.Instructor({
    estado: () => estado,
    ocupado: () => ocupado,
    consultar: consultarApi,
    preparar: prepararFormulaGuiada,
    cambiarEscenario: (escenario) => {
      estado = structuredClone(escenario);
      seleccionado = null;
      invalidarPrevisualizacion();
      lienzo.width = estado.mapa.ancho * TAM;
      lienzo.height = estado.mapa.alto * TAM;
      renderizar();
    },
    mostrarLectura,
    mostrarPrevisualizacion: (respuesta) => {
      previsualizacion = respuesta;
      $("costo").textContent = `⚡ ${respuesta.costo}`;
      mostrarLectura(respuesta.lectura);
      controles();
    },
    reiniciar: (paso) => iniciarPartida(configuracionAnterior, paso),
  });
  const tiposBase = {
    Infante: {
      mov: 3,
      alcance: 1,
      poder: 4,
    },
    Arquero: {
      mov: 2,
      alcance: 4,
      poder: 3,
    },
    Medico: {
      mov: 3,
      alcance: 2,
      poder: 3,
    },
    Tanque: {
      mov: 1,
      alcance: 2,
      poder: 5,
    },
  };
  const descripciones = {
    facil: "Ves objetivos, efectos y el árbol de justificación.",
    normal: "Ves cuántos enemigos y aliados recibirían el efecto.",
    dificil: "Solo validación de sintaxis y costo de energía.",
  };
  const nombres = {
    azul: "Azul",
    rojo: "Rojo",
    Infante: "Infante",
    Arquero: "Arquero",
    Medico: "Médico",
    Tanque: "Tanque",
  };
  // ------------------------ Utilidades de interfaz y comunicación con el servidor

  function nodo(etiqueta, clase, texto) {
    const n = document.createElement(etiqueta);
    if (clase) {
      n.className = clase;
    }
    if (texto !== undefined) {
      n.textContent = texto;
    }
    return n;
  }

  function unidad(id = seleccionado) {
    return estado?.unidades.find((u) => u.id === id);
  }

  function estadisticasUnidad(u) {
    return estado?.tipos?.[u.tipo] || tiposBase[u.tipo];
  }

  function mensaje(texto, error = false) {
    $("mensaje").textContent = texto;
    $("mensaje").classList.toggle("error", error);
  }

  function registrar(texto, bloque = null) {
    if (bloque) {
      bloque.querySelector(".registro-efectos").append(nodo("li", "", texto));
      return bloque;
    }
    const accion = nodo("li", "registro-bloque");
    accion.append(nodo("div", "registro-titulo", texto), nodo("ul", "registro-efectos"));
    $("registro").prepend(accion);
    $("registro").scrollTop = 0;
    while ($("registro").children.length > 30) {
      $("registro").lastChild.remove();
    }
    return accion;
  }

  async function consultarApi(accion, datos, senal) {
    let respuesta;
    try {
      respuesta = await fetch(`/api/juego/${accion}`, {
        method: datos === undefined ? "GET" : "POST",
        headers:
          datos === undefined
            ? {}
            : {
                "Content-Type": "application/json",
              },
        body: datos === undefined ? undefined : JSON.stringify(datos),
        signal: senal,
      });
    } catch (e) {
      if (e.name === "AbortError") {
        throw e;
      }
      throw new Error("No se pudo conectar con el servidor. Revisa la conexión e inténtalo de nuevo.");
    }
    let resultado;
    try {
      resultado = await respuesta.json();
    } catch {
      throw new Error(`El servidor no tiene disponible la API del juego (HTTP ${respuesta.status}).`);
    }
    if (!respuesta.ok || resultado.ok === false) {
      const e = new Error(
        (resultado.errores || []).map((x) => x.mensaje).join(" · ") || `Error del servidor (HTTP ${respuesta.status}).`,
      );
      e.errores = resultado.errores;
      throw e;
    }
    return resultado;
  }
  // ------------------------ Disponibilidad de controles y previsualización

  function invalidarPrevisualizacion() {
    secuenciaPrevisualizacion++;
    clearTimeout(temporizadorPrevisualizacion);
    previsualizacion = null;
    $("atacar").disabled = true;
    $("tooltip").hidden = true;
    $("errores-formula").replaceChildren();
    $("formula").removeAttribute("aria-invalid");
    $("formula-error-marca").hidden = true;
    $("resultado-preview").classList.remove("valido");
    $("costo").textContent = "⚡ —";
    mostrarLectura("");
  }

  function mostrarLectura(texto) {
    $("lectura-formula").textContent = texto ? `En español: ${texto}` : "";
    $("lectura-formula").hidden = !texto;
  }

  function prepararFormulaGuiada(formula, atacante) {
    seleccionado = atacante;
    editorAbierto = true;
    $("formula").value = normalizar(formula);
    invalidarPrevisualizacion();
    renderizarSeleccion();
    controles();
    programarPrevisualizacion();
  }

  function controles() {
    const u = unidad();
    const puede =
      !!u && u.bando === estado?.turno && !u.ataco && !estado?.ganador && !estado?.nivel_fallido && !ocupado;
    $("abrir-editor").disabled = !puede;
    $("terminar-turno").disabled = ocupado || !!estado?.ganador;
    $("atacar").disabled = !puede || !previsualizacion?.ok;
    $("abrir-menu").disabled = ocupado;
    $("formula").disabled = ocupado;
    document.querySelectorAll("#teclado button,#predicados button").forEach((b) => (b.disabled = ocupado));
    document.querySelectorAll(".unidad-fila").forEach((b) => {
      const v = unidad(b.dataset.unidad);
      b.disabled = ocupado || v?.bando !== estado?.turno || !!estado?.ganador;
    });
    instructor.actualizarControles(ocupado);
  }
  // ------------------------ Menú y configuración de la partida

  function dificultad() {
    ["azul", "rojo"].forEach((b) => {
      const s = $(`dificultad-${b}`);
      let texto = descripciones[s.value];
      if (b === "rojo" && modo === "cpu") {
        texto +=
          " CPU: " +
          {
            facil: "elige entre ataques aceptables.",
            normal: "elige entre sus tres mejores ataques.",
            dificil: "elige su mejor ataque.",
          }[s.value];
      }
      s.parentElement.querySelector("small").textContent = texto;
    });
  }

  function cambiarModo(nuevo) {
    modo = nuevo;
    document.querySelectorAll("[data-modo]").forEach((b) => {
      const activo = b.dataset.modo === modo;
      b.classList.toggle("activo", activo);
      b.setAttribute("aria-pressed", String(activo));
    });
    $("config-tutorial").hidden = modo !== "tutorial";
    $("config-dificultad").hidden = modo === "tutorial";
    $("nombre-rival").textContent = modo === "cpu" ? "CPU · BANDO ROJO" : "BANDO ROJO";
    $("iniciar").textContent = modo === "tutorial" ? "Comenzar misión →" : "Entrar en batalla →";
    $("iniciar").disabled = modo === "tutorial" && (cargandoNiveles || !niveles.length);
    dificultad();
  }

  function describirNivel() {
    const n = niveles.find((n) => String(n.id) === $("nivel").value);
    $("descripcion-nivel").textContent = n?.descripcion || "Elige una misión para comenzar.";
  }

  function actualizarProgresoLecciones() {
    const completadas = window.InstructorBatalla.leerProgreso();
    let cantidad = 0;
    niveles.forEach((nivel, indice) => {
      const completo = completadas.has(String(nivel.id));
      if (completo) cantidad++;
      $("nivel").options[indice].textContent =
        `${completo ? "✓ " : ""}${String(nivel.id).padStart(2, "0")} · ${nivel.titulo}`;
    });
    $("cantidad-lecciones").textContent = `${niveles.length} lecciones paso a paso`;
    $("progreso-lecciones").textContent = `${cantidad} de ${niveles.length} lecciones completadas en este navegador.`;
  }

  async function cargarNiveles() {
    if (cargandoNiveles) return;
    cargandoNiveles = true;
    $("reintentar-niveles").disabled = true;
    $("nivel").disabled = true;
    if (modo === "tutorial") $("iniciar").disabled = true;
    $("estado-menu").textContent = "Cargando lecciones…";
    try {
      const r = await consultarApi("niveles");
      niveles = r.niveles || [];
      $("nivel").replaceChildren();
      niveles.forEach((n) => {
        const o = nodo("option", "", `${String(n.id).padStart(2, "0")} · ${n.titulo}`);
        o.value = n.id;
        $("nivel").append(o);
      });
      $("nivel").disabled = !niveles.length;
      actualizarProgresoLecciones();
      const completadas = window.InstructorBatalla.leerProgreso();
      const pendiente = niveles.find((nivel) => !completadas.has(String(nivel.id)));
      if (pendiente) $("nivel").value = pendiente.id;
      describirNivel();
      $("estado-menu").textContent = "Elige tu misión. Cada decisión cuenta.";
      $("reintentar-niveles").hidden = true;
    } catch (e) {
      niveles = [];
      $("progreso-lecciones").textContent = "";
      $("estado-menu").textContent = e.message;
      $("nivel").replaceChildren(nodo("option", "", "Niveles no disponibles"));
      $("reintentar-niveles").hidden = false;
    } finally {
      cargandoNiveles = false;
      $("reintentar-niveles").disabled = false;
      cambiarModo(modo);
    }
  }

  async function iniciarPartida(config, pasoInicial = 0) {
    if (ocupado) {
      return;
    }
    ocupado = true;
    $("iniciar").disabled = true;
    $("estado-menu").textContent = "Desplegando escuadrones…";
    try {
      const r = await consultarApi("nueva", config);
      estado = r.estado;
      configuracionAnterior = config;
      seleccionado = null;
      editorAbierto = false;
      invalidarPrevisualizacion();
      $("formula").value = "";
      $("registro").replaceChildren();
      $("menu").hidden = true;
      $("partida").hidden = false;
      $("abrir-menu").hidden = false;
      $("indicacion-tablero").textContent = "Selecciona una unidad de tu bando";
      $("victoria").close();
      $("relevo").close();
      celdaCursor = null;
      animaciones = [];
      lienzo.width = estado.mapa.ancho * TAM;
      lienzo.height = estado.mapa.alto * TAM;
      await instructor.iniciar(
        niveles.find((nivel) => String(nivel.id) === String(estado.nivel)),
        estado,
        pasoInicial,
      );
      renderizar();
      mensaje(
        estado.modo === "tutorial"
          ? "Lee al instructor y avanza a tu ritmo. Las unidades señaladas están relacionadas con la explicación."
          : "Selecciona una unidad de tu bando. Las casillas iluminadas indican su movimiento.",
      );
      registrar(
        estado.modo === "tutorial"
          ? `Misión ${estado.nivel}: ${niveles.find((n) => n.id === estado.nivel)?.titulo || "Entrenamiento"}`
          : "Comienza la batalla. El bando Azul toma el mando.",
      );
      iniciarDibujo();
    } catch (e) {
      $("estado-menu").textContent = e.message;
      mensaje(e.message, true);
    } finally {
      ocupado = false;
      $("iniciar").disabled = modo === "tutorial" && !niveles.length;
      controles();
    }
  }

  function iniciarDesdeMenu() {
    const config = {
      modo,
      dificultad: {
        azul: $("dificultad-azul").value,
        rojo: $("dificultad-rojo").value,
      },
    };
    if (modo === "tutorial") {
      config.nivel = niveles.find((n) => String(n.id) === $("nivel").value)?.id;
    }
    iniciarPartida(config);
  }
  // ------------------------ HUD, escuadrones y panel del tutorial

  function renderizar() {
    if (!estado) {
      return;
    }
    $("turno-numero").textContent = `Turno ${String(estado.numero_turno).padStart(2, "0")}`;
    $("bando-turno").textContent = nombres[estado.turno];
    $("bando-turno").classList.toggle("rojo", estado.turno === "rojo");
    $("modo-partida").textContent = {
      cpu: "CONTRA LA CPU",
      local: "DOS JUGADORES",
      tutorial: `TUTORIAL · MISIÓN ${estado.nivel}`,
    }[estado.modo];
    const max = estado.energia_maxima || estado.parametros?.energia_maxima || 15;
    $("energia-valor").textContent = `${estado.energia[estado.turno]} / ${max}`;
    $("energia-barra").style.width = `${Math.min(100, (estado.energia[estado.turno] / max) * 100)}%`;
    $("cantidad-unidades").textContent = `${estado.unidades.length} EN PIE`;
    $("lista-unidades").replaceChildren();
    ["azul", "rojo"].forEach((b) => {
      $("lista-unidades").append(
        nodo(
          "p",
          "grupo-bando",
          `${nombres[b].toUpperCase()} · ${estado.unidades.filter((u) => u.bando === b).length} UNIDADES`,
        ),
      );
      estado.unidades
        .filter((u) => u.bando === b)
        .forEach((u) => {
          const boton = nodo("button", `unidad-fila ${b}${u.id === seleccionado ? " elegida" : ""}`);
          boton.type = "button";
          boton.setAttribute(
            "aria-label",
            `${u.id}, ${nombres[u.tipo]}, ${nombres[b]}, vida ${u.vida} de ${u.vida_max}${u.ataco ? ", ya atacó" : ""}${
              u.movio ? ", ya se movió" : ""
            }`,
          );
          boton.setAttribute("aria-pressed", String(u.id === seleccionado));
          boton.dataset.unidad = u.id;
          boton.disabled = ocupado || u.bando !== estado.turno || !!estado.ganador;
          const info = nodo("div", "unidad-info");
          const cab = nodo("div");
          cab.append(nodo("strong", "", `${u.id} · ${nombres[u.tipo]}`), nodo("small", "", `${u.vida}/${u.vida_max}`));
          const barra = nodo("div", "barra-vida");
          const relleno = nodo("i");
          relleno.style.width = `${(u.vida / u.vida_max) * 100}%`;
          barra.append(relleno);
          info.append(cab, barra);
          boton.append(
            arte.retrato(u),
            info,
            nodo("span", "acciones-unidad", `${u.movio ? "" : "↟"}${u.ataco ? "" : "✦"}`),
          );
          boton.addEventListener("click", () => elegir(u.id));
          $("lista-unidades").append(boton);
        });
    });
    renderizarSeleccion();
    renderizarTutorial();
    controles();
  }

  function renderizarSeleccion() {
    const u = unidad();
    const d = $("unidad-detalle");
    d.replaceChildren();
    if (!u) {
      d.append(nodo("p", "vacio", "Selecciona a un soldado en el campo o en tu escuadrón."));
      return;
    }
    const cab = nodo("div", "unidad-cabecera");
    const info = nodo("div");
    info.append(
      nodo("h2", "", `${u.id} · ${nombres[u.tipo]}`),
      nodo("small", "", `${nombres[u.bando]} · ${u.tipo === "Medico" ? "Cura en área" : "Ataque en área"}`),
    );
    cab.append(arte.retrato(u), info);
    const est = nodo("div", "estadisticas");
    const s = estadisticasUnidad(u);
    [
      [`${u.vida}/${u.vida_max}`, "VIDA"],
      [s.mov, "MOV."],
      [s.alcance, "ALCANCE"],
      [s.poder, u.tipo === "Medico" ? "CURA" : "PODER"],
    ].forEach(([valor, titulo]) => {
      const n = nodo("span");
      n.append(nodo("b", "", valor), document.createTextNode(titulo));
      est.append(n);
    });
    d.append(
      cab,
      est,
      nodo(
        "p",
        "micro",
        `${u.movio ? "✓ Movimiento usado" : "↟ Movimiento disponible"} · ${
          u.ataco ? "✓ Ataque usado" : "✦ Ataque disponible"
        }`,
      ),
    );
    $("abrir-editor").firstChild.textContent = u.tipo === "Medico" ? "Preparar cura " : "Preparar ataque ";
  }

  function renderizarTutorial() {
    if (instructor.activo) {
      $("panel-tutorial").hidden = true;
      return;
    }
    $("panel-tutorial").hidden = estado.modo !== "tutorial";
    if (estado.modo !== "tutorial") {
      return;
    }
    const n = niveles.find((n) => String(n.id) === String(estado.nivel)) || {};
    $("titulo-nivel").textContent = `${String(estado.nivel).padStart(2, "0")} / ${n.titulo || "Entrenamiento"}`;
    $("texto-nivel").textContent = n.explicacion || n.descripcion || "";
    $("objetivo-nivel").textContent = n.objetivo || n.descripcion || "Elimina al rival con una fórmula precisa.";
    $("pista-nivel").textContent = n.pista || "Revisa qué unidades cumplen la fórmula.";
    $("simbolos-nivel").textContent = `Símbolos de la misión: ${(n.simbolos || []).join(" · ")}`;
  }
  // ------------------------ Selección y movimiento por terreno ponderado

  function elegir(id) {
    if (instructor.activo && id !== instructor.atacante) {
      mensaje("En esta lección lanzamos la fórmula con el atacante indicado por el instructor.");
      return;
    }
    const u = unidad(id);
    if (ocupado || !u || u.bando !== estado.turno || estado.ganador) {
      return;
    }
    seleccionado = id;
    invalidarPrevisualizacion();
    renderizar();
    $("indicacion-tablero").textContent = u.movio
      ? "Movimiento usado · prepara una fórmula"
      : "Casillas verdes: movimiento disponible";
    mensaje(
      `${u.id} · ${nombres[u.tipo]}. ${
        u.ataco
          ? "Ya atacó este turno."
          : u.tipo === "Medico"
            ? "Puede curar a los objetivos de la fórmula."
            : "Prepara una fórmula para atacar."
      }`,
    );
    programarPrevisualizacion();
  }

  function alcanzables(u) {
    if (!u || u.movio || u.bando !== estado.turno || ocupado || instructor.activo) {
      return new Map();
    }
    const clave = (x, y) => `${x},${y}`;
    const dist = new Map([[clave(u.col, u.fila), 0]]);
    const cola = [[u.col, u.fila]];
    const ocupadas = new Set(estado.unidades.filter((v) => v.id !== u.id).map((v) => clave(v.col, v.fila)));
    while (cola.length) {
      const [x, y] = cola.shift();
      for (const [nx, ny] of [
        [x + 1, y],
        [x - 1, y],
        [x, y + 1],
        [x, y - 1],
      ]) {
        if (
          nx < 0 ||
          ny < 0 ||
          nx >= estado.mapa.ancho ||
          ny >= estado.mapa.alto ||
          ocupadas.has(clave(nx, ny)) ||
          estado.mapa.terreno[ny][nx] === "muro"
        ) {
          continue;
        }
        const costo = dist.get(clave(x, y)) + (estado.mapa.terreno[ny][nx] === "agua" ? 2 : 1);
        if (costo <= estadisticasUnidad(u).mov && costo < (dist.get(clave(nx, ny)) ?? Infinity)) {
          dist.set(clave(nx, ny), costo);
          cola.push([nx, ny]);
        }
      }
    }
    dist.delete(clave(u.col, u.fila));
    return dist;
  }
  // Recupera la ruta ponderada para que las animaciones también rodeen los muros.

  function ruta(u, destino) {
    const clave = (x, y) => `${x},${y}`;
    const inicio = clave(u.col, u.fila);
    const final = clave(...destino);
    const dist = new Map([[inicio, 0]]);
    const anteriores = new Map();
    const cola = [[u.col, u.fila]];
    const ocupadas = new Set(estado.unidades.filter((v) => v.id !== u.id).map((v) => clave(v.col, v.fila)));
    while (cola.length) {
      const [x, y] = cola.shift();
      for (const [nx, ny] of [
        [x + 1, y],
        [x - 1, y],
        [x, y + 1],
        [x, y - 1],
      ]) {
        if (
          nx < 0 ||
          ny < 0 ||
          nx >= estado.mapa.ancho ||
          ny >= estado.mapa.alto ||
          estado.mapa.terreno[ny][nx] === "muro" ||
          (ocupadas.has(clave(nx, ny)) && clave(nx, ny) !== final)
        ) {
          continue;
        }
        const k = clave(nx, ny);
        const c = dist.get(clave(x, y)) + (estado.mapa.terreno[ny][nx] === "agua" ? 2 : 1);
        if (c < (dist.get(k) ?? Infinity)) {
          dist.set(k, c);
          anteriores.set(k, clave(x, y));
          cola.push([nx, ny]);
        }
      }
    }
    if (!dist.has(final)) {
      return [[u.col, u.fila], destino];
    }
    const pasos = [destino];
    let k = final;
    while (k !== inicio) {
      k = anteriores.get(k);
      pasos.unshift(k.split(",").map(Number));
    }
    return pasos;
  }

  async function accionarCelda(col, fila) {
    if (!estado || ocupado || estado.ganador) {
      return;
    }
    const u = estado.unidades.find((u) => u.col === col && u.fila === fila);
    if (u) {
      if (u.bando === estado.turno) {
        elegir(u.id);
      } else {
        mensaje("Es una unidad rival. Selecciona una unidad propia y usa una fórmula para alcanzarla.");
      }
      return;
    }
    const propia = unidad();
    if (!propia) {
      mensaje("Primero selecciona una unidad de tu bando.");
      return;
    }
    if (instructor.activo && instructor.paso.tipo === "reto") {
      await realizar("mover", { unidad: propia.id, destino: [col, fila] });
      return;
    }
    if (!alcanzables(propia).has(`${col},${fila}`)) {
      mensaje("Esa casilla no es alcanzable. Revisa el terreno y el movimiento disponible.", true);
      return;
    }
    await realizar("mover", {
      unidad: propia.id,
      destino: [col, fila],
    });
  }
  // ------------------------ Editor de fórmulas y validación en vivo

  function normalizar(texto) {
    return texto
      .replace(/forall\b/gi, "∀")
      .replace(/exists\b/gi, "∃")
      .replace(/->|=>/g, "→")
      .replace(/\/\\/g, "∧")
      .replace(/\\\//g, "∨")
      .replace(/[~!]/g, "¬")
      .replace(/&/g, "∧")
      .replace(/\|/g, "∨");
  }

  function entradaFormula() {
    const campo = $("formula");
    const inicio = campo.selectionStart;
    const fin = campo.selectionEnd;
    const original = campo.value;
    campo.value = normalizar(original);
    campo.setSelectionRange(normalizar(original.slice(0, inicio)).length, normalizar(original.slice(0, fin)).length);
    instructor.formulaEditada();
    programarPrevisualizacion();
  }

  function insertar(texto) {
    const campo = $("formula");
    if (ocupado || instructor.procesando || instructor.escribiendo) {
      return;
    }
    campo.setRangeText(texto, campo.selectionStart, campo.selectionEnd, "end");
    campo.focus();
    entradaFormula();
  }

  function programarPrevisualizacion() {
    invalidarPrevisualizacion();
    const u = unidad();
    if (instructor.activo && $("formula").value.includes("___")) {
      $("resultado-preview").textContent =
        "Completa los huecos ___ y pulsa Comprobar. Puedes intentarlo cuantas veces quieras.";
      return;
    }
    if (
      !u ||
      u.ataco ||
      !$("formula").value.trim() ||
      ocupado ||
      estado?.ganador ||
      estado?.nivel_fallido ||
      instructor.escribiendo ||
      instructor.procesando ||
      (instructor.activo && instructor.fallo)
    ) {
      $("resultado-preview").textContent = u?.ataco
        ? "Esta unidad ya atacó durante este turno."
        : "Selecciona una unidad y escribe una fórmula.";
      return;
    }
    $("resultado-preview").textContent = "Comprobando fórmula…";
    const numero = secuenciaPrevisualizacion;
    temporizadorPrevisualizacion = setTimeout(() => previsualizar(numero), 250);
  }

  function erroresFormula(e) {
    $("formula").setAttribute("aria-invalid", "true");
    $("errores-formula").replaceChildren();
    const errores = e.errores || [
      {
        mensaje: e.message,
      },
    ];
    errores.forEach((x) =>
      $("errores-formula").append(
        nodo("li", "", `${x.mensaje}${Number.isInteger(x.posicion) ? ` (posición ${x.posicion})` : ""}`),
      ),
    );
    const error = errores.find((x) => Number.isInteger(x.posicion));
    if (error) {
      const texto = $("formula").value;
      const p = Math.max(0, Math.min(texto.length, error.posicion));
      const marca = $("formula-error-marca");
      marca.replaceChildren(
        document.createTextNode(texto.slice(0, p)),
        nodo("mark", "", texto[p] || "▏"),
        document.createTextNode(texto.slice(p + 1)),
      );
      marca.hidden = false;
    }
  }

  async function previsualizar(numero) {
    const u = unidad();
    if (!u || ocupado) {
      return;
    }
    try {
      const r = await consultarApi("previsualizar", {
        estado,
        atacante: u.id,
        formula: $("formula").value.trim(),
      });
      if (numero !== secuenciaPrevisualizacion) {
        return;
      }
      previsualizacion = r;
      mostrarLectura(r.nivel_detalle === "completo" ? r.lectura : "");
      $("costo").textContent = `⚡ ${r.costo}`;
      const n = $("resultado-preview");
      n.replaceChildren();
      n.classList.add("valido");
      if (r.nivel_detalle === "sintaxis") {
        n.textContent = `Fórmula válida · costo ${r.costo}. Esta dificultad no muestra los objetivos.`;
      } else {
        const { enemigos = 0, aliados = 0 } = r.resumen || {};
        const cura = u.tipo === "Medico";
        n.append(
          nodo(
            "div",
            "",
            `${cura ? "Curarías" : "Golpearías"} a ${enemigos} enemigo${enemigos === 1 ? "" : "s"} y ${aliados} aliado${
              aliados === 1 ? "" : "s"
            }.`,
          ),
        );
        if ((!cura && aliados) || (cura && enemigos)) {
          n.append(
            nodo(
              "div",
              "riesgo",
              cura ? "⚠ También curarías al rival." : "⚠ Fuego amigo: tus aliados recibirían daño.",
            ),
          );
        }
        if (r.nivel_detalle === "completo") {
          const objetivos = (r.objetivos || []).filter((o) => o.cumple && o.en_alcance);
          const k = objetivos.length;
          const efecto = cura
            ? estadisticasUnidad(u).poder
            : estadisticasUnidad(u).poder + (k === 1 ? 2 : k === 2 ? 1 : 0);
          const detalle = objetivos
            .map((o) => `${o.id} (${cura ? "+" : "−"}${o.cantidad ?? efecto}${o.baja ? ", baja" : ""})`)
            .join(", ");
          n.append(
            nodo(
              "div",
              "",
              `${
                objetivos.length ? `${detalle} PV.` : "Ningún objetivo: gastarás energía sin efecto."
              } Pasa el cursor para ver las razones.`,
            ),
          );
        }
      }
      controles();
    } catch (e) {
      if (numero !== secuenciaPrevisualizacion) {
        return;
      }
      previsualizacion = null;
      $("resultado-preview").textContent = "Revisa la fórmula antes de ejecutarla.";
      erroresFormula(e);
      controles();
    }
  }
  // ------------------------ Acciones, eventos de combate y cambio de turno

  async function realizar(accion, datos = {}) {
    if (ocupado || !estado || estado.ganador) {
      return;
    }
    if (instructor.activo && (!instructor.permiteAtaque || !["atacar", "mover"].includes(accion))) return;
    ocupado = true;
    invalidarPrevisualizacion();
    controles();
    $("tooltip").hidden = true;
    const turnoAnterior = estado.turno;
    mensaje(
      accion === "terminar_turno" && estado.modo === "cpu" ? "La CPU está preparando su turno…" : "Procesando orden…",
    );
    try {
      const r = await consultarApi(accion, {
        estado,
        ...datos,
      });
      const eventos =
        r.eventos ||
        (r.evento
          ? [r.evento]
          : accion === "mover"
            ? [
                {
                  tipo: "mover",
                  unidad: datos.unidad,
                  destino: datos.destino,
                },
              ]
            : []);
      await reproducir(eventos);
      estado = r.estado;
      if (accion === "atacar") instructor.observarResultado(r);
      if (!unidad() || accion === "terminar_turno") {
        seleccionado = null;
      }
      renderizar();
      if (estado.ganador || estado.nivel_completado || estado.nivel_superado || r.nivel_superado) {
        mostrarVictoria();
      } else if (estado.modo === "local" && estado.turno !== turnoAnterior) {
        seleccionado = null;
        editorAbierto = false;
        $("formula").value = "";
        $("titulo-relevo").textContent = `Turno de ${nombres[estado.turno]}`;
        $("relevo").showModal();
        mensaje(`Turno de ${nombres[estado.turno]}. Pasa el teclado al siguiente jugador.`);
      } else if (accion === "terminar_turno") {
        mensaje("Tu turno. Selecciona una unidad para continuar.");
      } else if (accion === "mover") {
        mensaje("Posición asegurada. Puedes preparar una fórmula con esta unidad.");
      } else {
        mensaje(
          eventos.find((e) => e.tipo === "mensaje")?.mensaje ||
            "Orden ejecutada. Selecciona otra unidad o termina el turno.",
        );
      }
    } catch (e) {
      mensaje(e.message, true);
      if (instructor.activo && accion === "mover") instructor.mostrarFeedback({ mensaje: e.message });
      if (accion === "atacar") {
        erroresFormula(e);
      }
    } finally {
      ocupado = false;
      renderizar();
      programarPrevisualizacion();
    }
  }
  const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, reducido.matches ? 0 : ms));

  function efecto(datos, duracion) {
    if (reducido.matches) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      animaciones.push({
        ...datos,
        inicio: performance.now(),
        duracion,
        resolve,
      });
      iniciarDibujo();
    });
  }

  async function reproducir(eventos) {
    let atacante = null;
    let bloqueAtaque = null;
    for (const e of eventos) {
      if (e.tipo === "mover") {
        const u = unidad(e.unidad);
        if (!u || !e.destino) {
          continue;
        }
        const pasos = ruta(u, e.destino);
        await efecto(
          {
            tipo: "mover",
            unidad: u.id,
            pasos,
          },
          Math.max(200, (pasos.length - 1) * 140),
        );
        u.col = e.destino[0];
        u.fila = e.destino[1];
        bloqueAtaque = null;
        registrar(`${e.unidad} se movió a (${e.destino[0] + 1}, ${e.destino[1] + 1}).`);
      } else if (e.tipo === "ataque") {
        atacante = unidad(e.atacante);
        const cpu = estado.modo === "cpu" && atacante?.bando === "rojo";
        const texto = `${cpu ? "La CPU lanzó" : `${e.atacante} lanzó`}: ${e.formula}`;
        bloqueAtaque = registrar(texto);
        mensaje(texto);
        if (cpu) {
          $("aviso-tablero").textContent = texto;
          $("aviso-tablero").hidden = false;
          await esperar(650);
          $("aviso-tablero").hidden = true;
        }
      } else if (e.tipo === "danio" || e.tipo === "cura") {
        const u = unidad(e.unidad || e.objetivo);
        if (!u) {
          continue;
        }
        const cura = e.tipo === "cura";
        if (atacante) {
          await efecto(
            {
              tipo: "rayo",
              desde: [atacante.col, atacante.fila],
              hasta: [u.col, u.fila],
              cura,
            },
            240,
          );
        }
        if (!cura && !reducido.matches) {
          lienzo.classList.remove("temblor");
          void lienzo.offsetWidth;
          lienzo.classList.add("temblor");
        }
        await efecto(
          {
            tipo: "impacto",
            col: u.col,
            fila: u.fila,
            cura,
            cantidad: e.cantidad ?? e.danio ?? 0,
          },
          430,
        );
        const cantidad = e.cantidad ?? e.danio ?? 0;
        u.vida = Math.max(0, Math.min(u.vida_max, u.vida + (cura ? cantidad : -cantidad)));
        registrar(`${u.id}: ${cura ? "+" : "−"}${cantidad} PV ${cura ? "de curación" : "de daño"}.`, bloqueAtaque);
      } else if (e.tipo === "baja") {
        const id = e.unidad || e.objetivo;
        const u = unidad(id);
        if (u) {
          await efecto(
            {
              tipo: "baja",
              unidad: id,
            },
            320,
          );
        }
        estado.unidades = estado.unidades.filter((u) => u.id !== id);
        registrar(`${id} cayó en combate.`, bloqueAtaque);
      } else if (e.tipo === "mensaje") {
        registrar(e.mensaje || "Nadie cumplió la fórmula.", bloqueAtaque);
      }
    }
  }
  // ------------------------ Fin de misión y regreso al menú

  function mostrarVictoria() {
    const tutorial =
      estado.modo === "tutorial" && (estado.ganador === "azul" || estado.nivel_completado || estado.nivel_superado);
    const indice = niveles.findIndex((n) => String(n.id) === String(estado.nivel));
    const ultimaLeccion = tutorial && indice >= 0 && indice === niveles.length - 1;
    const derrotaCpu = estado.modo === "cpu" && estado.ganador === "rojo";
    if (ultimaLeccion) {
      $("titulo-victoria").textContent = "¡Tutorial completado!";
      $("texto-victoria").textContent = "Completaste todas las lecciones. Pon en práctica lo aprendido contra la CPU.";
    } else if (tutorial) {
      $("titulo-victoria").textContent = "¡Misión superada!";
      $("texto-victoria").textContent = "Tu fórmula decidió el combate. Continúa con el siguiente concepto.";
    } else if (estado.modo === "cpu") {
      $("titulo-victoria").textContent = derrotaCpu ? "Derrota" : "¡Victoria!";
      $("texto-victoria").textContent = derrotaCpu
        ? "La CPU eliminó a tu escuadrón. Puedes intentarlo de nuevo."
        : "Eliminaste al ejército de la CPU. ¡Buen trabajo!";
    } else {
      $("titulo-victoria").textContent = `¡Victoria de ${nombres[estado.ganador] || "tu escuadrón"}!`;
      $("texto-victoria").textContent = "El ejército rival ha sido eliminado del universo.";
    }
    $("ceja-victoria").textContent = ultimaLeccion
      ? "ENTRENAMIENTO COMPLETADO"
      : tutorial
        ? "FÓRMULA RESUELTA"
        : derrotaCpu
          ? "FIN DE LA PARTIDA"
          : "OPERACIÓN COMPLETADA";
    $("siguiente-nivel").hidden = !tutorial || indice < 0 || ultimaLeccion;
    $("ir-cpu").hidden = !ultimaLeccion;
    if (tutorial) actualizarProgresoLecciones();
    if (!$("victoria").open) {
      $("victoria").showModal();
    }
  }

  function volverMenu() {
    if (ocupado) {
      return;
    }
    $("victoria").close();
    $("relevo").close();
    instructor.detener();
    invalidarPrevisualizacion();
    $("partida").hidden = true;
    $("menu").hidden = false;
    $("abrir-menu").hidden = true;
    cancelAnimationFrame(fotograma);
    fotograma = 0;
    $("estado-menu").textContent = "Elige tu próxima misión.";
    $("iniciar").focus();
  }
  // ------------------------ Dibujo del tablero y animaciones

  function iniciarDibujo() {
    if (!fotograma && !$("partida").hidden) {
      fotograma = requestAnimationFrame(dibujar);
    }
  }

  function dibujar(tiempo) {
    fotograma = 0;
    if (!estado || $("partida").hidden) {
      return;
    }
    contexto.imageSmoothingEnabled = false;
    contexto.clearRect(0, 0, lienzo.width, lienzo.height);
    for (let f = 0; f < estado.mapa.alto; f++) {
      for (let c = 0; c < estado.mapa.ancho; c++) {
        arte.terreno(contexto, estado.mapa.terreno[f][c], c, f, TAM, reducido.matches ? 0 : tiempo);
        contexto.strokeStyle = "#102c2320";
        contexto.lineWidth = 1;
        contexto.strokeRect(c * TAM + 0.5, f * TAM + 0.5, TAM, TAM);
      }
    }
    const u = unidad();
    const movimientos = alcanzables(u);
    if (u) {
      if ((editorAbierto || previsualizacion) && (!instructor.activo || instructor.paso.tipo !== "explicacion")) {
        for (let f = 0; f < estado.mapa.alto; f++) {
          for (let c = 0; c < estado.mapa.ancho; c++) {
            const d = Math.abs(c - u.col) + Math.abs(f - u.fila);
            if (d > 0 && d <= estadisticasUnidad(u).alcance) {
              contexto.fillStyle = "#f4dfa220";
              contexto.fillRect(c * TAM, f * TAM, TAM, TAM);
              contexto.strokeStyle = "#e8d88b55";
              contexto.setLineDash([4, 5]);
              contexto.strokeRect(c * TAM + 3, f * TAM + 3, TAM - 6, TAM - 6);
              contexto.setLineDash([]);
            }
          }
        }
      }
      movimientos.forEach((costo, clave) => {
        const [c, f] = clave.split(",").map(Number);
        contexto.fillStyle = "#d5ee892e";
        contexto.fillRect(c * TAM + 3, f * TAM + 3, TAM - 6, TAM - 6);
        contexto.strokeStyle = "#d5ee8988";
        contexto.strokeRect(c * TAM + 3, f * TAM + 3, TAM - 6, TAM - 6);
        contexto.fillStyle = "#e4f0ba";
        contexto.font = "11px Consolas,monospace";
        contexto.fillText(String(costo), c * TAM + 8, f * TAM + 15);
      });
      contexto.strokeStyle = "#e0f59d";
      contexto.lineWidth = 3;
      contexto.strokeRect(u.col * TAM + 3, u.fila * TAM + 3, TAM - 6, TAM - 6);
    }
    const datos = new Map(
      (previsualizacion?.nivel_detalle === "completo" ? previsualizacion.objetivos || [] : []).map((o) => [o.id, o]),
    );
    for (const v of [...estado.unidades].sort((a, b) => a.fila - b.fila)) {
      let col = v.col;
      let fila = v.fila;
      let opacidad = 1;
      const mov = animaciones.find((a) => a.tipo === "mover" && a.unidad === v.id);
      if (mov && mov.pasos.length > 1) {
        const p = Math.max(0, Math.min(1, (tiempo - mov.inicio) / mov.duracion)) * (mov.pasos.length - 1);
        const i = Math.min(mov.pasos.length - 2, Math.floor(p));
        const t = p - i;
        col = mov.pasos[i][0] + (mov.pasos[i + 1][0] - mov.pasos[i][0]) * t;
        fila = mov.pasos[i][1] + (mov.pasos[i + 1][1] - mov.pasos[i][1]) * t;
      }
      const baja = animaciones.find((a) => a.tipo === "baja" && a.unidad === v.id);
      if (baja) {
        opacidad = 1 - Math.min(1, (tiempo - baja.inicio) / baja.duracion);
      }
      const o = datos.get(v.id);
      if (o && !o.en_alcance && v.id !== seleccionado) {
        opacidad *= 0.38;
      }
      const x = col * TAM;
      const y = fila * TAM;
      contexto.fillStyle = v.bando === "azul" ? "#5ac4f0" : "#ff8b7c";
      contexto.globalAlpha = opacidad * 0.8;
      contexto.fillRect(x + 25, y + 66, 30, 5);
      contexto.globalAlpha = 1;
      const escala = 4;
      arte.soldado(contexto, v.tipo, v.bando, x + 16, y + 8, escala, opacidad);
      contexto.globalAlpha = opacidad;
      contexto.fillStyle = "#11231d";
      contexto.fillRect(x + 17, y + 4, 46, 5);
      contexto.fillStyle = v.bando === "azul" ? "#80d5e9" : "#ffa284";
      contexto.fillRect(x + 17, y + 4, (46 * Math.max(0, v.vida)) / v.vida_max, 5);
      contexto.fillStyle = "#eef6df";
      contexto.font = "10px Consolas,monospace";
      contexto.textAlign = "center";
      contexto.fillText(v.id, x + 40, y + 78);
      contexto.textAlign = "left";
      contexto.globalAlpha = 1;
      if (v.ataco) {
        contexto.fillStyle = "#15281c99";
        contexto.fillRect(x + 61, y + 64, 12, 12);
        contexto.fillStyle = "#d5ee89";
        contexto.fillText("✓", x + 62, y + 74);
      }
      if (o?.cumple && o.en_alcance) {
        const colorMira = o.aliado ? "#ffdc79" : "#ff7b69";
        contexto.strokeStyle = colorMira;
        contexto.lineWidth = 2;
        const cx = x + 40;
        const cy = y + 37;
        contexto.beginPath();
        contexto.arc(cx, cy, 25, 0, Math.PI * 2);
        contexto.moveTo(cx - 32, cy);
        contexto.lineTo(cx - 16, cy);
        contexto.moveTo(cx + 16, cy);
        contexto.lineTo(cx + 32, cy);
        contexto.moveTo(cx, cy - 32);
        contexto.lineTo(cx, cy - 16);
        contexto.moveTo(cx, cy + 16);
        contexto.lineTo(cx, cy + 32);
        contexto.stroke();
        if (o.aliado) {
          contexto.fillStyle = "#ffdc79";
          contexto.font = "bold 18px Consolas,monospace";
          contexto.fillText("!", x + 64, y + 23);
        }
      }
    }
    instructor.dibujar(contexto, TAM, tiempo);
    if (celdaCursor) {
      contexto.strokeStyle = "#f0f7e0";
      contexto.lineWidth = 2;
      contexto.strokeRect(celdaCursor[0] * TAM + 1, celdaCursor[1] * TAM + 1, TAM - 2, TAM - 2);
    }
    for (const a of animaciones) {
      const p = Math.max(0, Math.min(1, (tiempo - a.inicio) / a.duracion));
      if (a.tipo === "rayo") {
        const [x, y] = a.desde.map((v) => (v + 0.5) * TAM);
        const [tx, ty] = a.hasta.map((v) => (v + 0.5) * TAM);
        contexto.strokeStyle = a.cura ? "#bcefa3" : "#ffe6a5";
        contexto.lineWidth = 3;
        contexto.beginPath();
        contexto.moveTo(x, y);
        contexto.lineTo(x + (tx - x) * p, y + (ty - y) * p);
        contexto.stroke();
        contexto.fillStyle = a.cura ? "#dcffbf" : "#fff6cc";
        contexto.fillRect(x + (tx - x) * p - 5, y + (ty - y) * p - 5, 10, 10);
      } else if (a.tipo === "impacto") {
        const x = (a.col + 0.5) * TAM;
        const y = (a.fila + 0.5) * TAM;
        contexto.save();
        contexto.globalAlpha = 1 - p;
        contexto.strokeStyle = a.cura ? "#bcefa3" : "#ffcb82";
        contexto.lineWidth = 5 * (1 - p);
        contexto.strokeRect(x - 28 * p, y - 28 * p, 56 * p, 56 * p);
        for (let j = 0; j < 8; j++) {
          const ang = (j * Math.PI) / 4;
          contexto.fillStyle = j % 2 ? "#fff0b1" : a.cura ? "#c8f4a2" : "#ee9161";
          contexto.fillRect(x + Math.cos(ang) * 40 * p - 3, y + Math.sin(ang) * 40 * p - 3, 6, 6);
        }
        contexto.globalAlpha = Math.min(1, (1 - p) * 2);
        contexto.font = "bold 26px Consolas,monospace";
        contexto.textAlign = "center";
        contexto.lineWidth = 4;
        contexto.strokeStyle = "#172a23";
        const texto = `${a.cura ? "+" : "−"}${a.cantidad}`;
        contexto.strokeText(texto, x, y - 15 - p * 30);
        contexto.fillStyle = a.cura ? "#c9ffb2" : "#fff0cf";
        contexto.fillText(texto, x, y - 15 - p * 30);
        contexto.restore();
      }
    }
    const finalizadas = animaciones.filter((a) => tiempo - a.inicio >= a.duracion);
    animaciones = animaciones.filter((a) => tiempo - a.inicio < a.duracion);
    finalizadas.forEach((a) => a.resolve());
    fotograma = requestAnimationFrame(dibujar);
  }
  // ------------------------ Árbol de justificación y navegación del tablero

  function construirArbol(
    arbol,
    profundidad = 0,
    presupuesto = {
      n: 0,
    },
  ) {
    const lista = nodo("ul");
    if (!arbol) {
      return lista;
    }
    if (profundidad > 15 || presupuesto.n++ > 250) {
      lista.append(nodo("li", "micro", "Árbol extenso: se muestran las primeras 250 comprobaciones."));
      return lista;
    }
    const item = nodo(
      "li",
      "",
      `${arbol.valor ? "✓" : "✕"} ${arbol.tipo || "comprobación"}: ${arbol.explicacion || arbol.formula || ""}`,
    );
    if (arbol.asignacion) {
      item.append(nodo("div", "micro", arbol.asignacion));
    }
    (arbol.hijos || []).forEach((h) => {
      if (presupuesto.n <= 250) {
        item.append(construirArbol(h, profundidad + 1, presupuesto));
      }
    });
    lista.append(item);
    return lista;
  }

  function mostrarJustificacion(col, fila) {
    const u = estado?.unidades.find((u) => u.col === col && u.fila === fila);
    const t = $("tooltip");
    if (!u || ocupado || previsualizacion?.nivel_detalle !== "completo") {
      t.hidden = true;
      return;
    }
    const o = previsualizacion.objetivos?.find((o) => o.id === u.id);
    if (!o) {
      t.hidden = true;
      return;
    }
    const alcance =
      u.id === seleccionado
        ? "es el atacante: no se ataca a sí mismo"
        : o.en_alcance
          ? "en alcance"
          : "fuera de alcance";
    t.replaceChildren(
      nodo("h3", "", `${u.id} · ${nombres[u.tipo]}`),
      nodo("p", "", `${o.cumple ? "Cumple" : "No cumple"} la fórmula · ${alcance}`),
    );
    if (o.cumple && o.en_alcance && o.cantidad !== undefined) {
      t.append(
        nodo(
          "p",
          "",
          `${o.efecto === "cura" ? "Curación" : "Daño"}: ${o.cantidad} PV${o.baja ? " · Baja prevista" : ""}`,
        ),
      );
    }
    if (o.arbol) {
      const arbol = construirArbol(o.arbol);
      if (instructor.activo) {
        const detalle = nodo("details");
        detalle.append(nodo("summary", "", "Ver detalle"), arbol);
        t.append(detalle);
      } else t.append(arbol);
    }
    t.hidden = false;
    const contenedor = lienzo.parentElement;
    const ancho = contenedor.clientWidth;
    const alto = contenedor.clientHeight;
    const izquierda = lienzo.offsetLeft + ((col + 0.5) / estado.mapa.ancho) * lienzo.clientWidth;
    const arriba = lienzo.offsetTop + ((fila + 0.5) / estado.mapa.alto) * lienzo.clientHeight;
    t.style.left = `${Math.max(4, Math.min(ancho - t.offsetWidth - 4, izquierda + 18))}px`;
    t.style.top = `${Math.max(4, Math.min(alto - t.offsetHeight - 4, arriba + 15))}px`;
  }

  function coordenada(e) {
    const r = lienzo.getBoundingClientRect();
    return [
      Math.min(estado.mapa.ancho - 1, Math.max(0, Math.floor(((e.clientX - r.left) / r.width) * estado.mapa.ancho))),
      Math.min(estado.mapa.alto - 1, Math.max(0, Math.floor(((e.clientY - r.top) / r.height) * estado.mapa.alto))),
    ];
  }
  // ------------------------ Entrada por ratón y teclado

  lienzo.addEventListener("click", (e) => {
    if (!estado) {
      return;
    }
    const [c, f] = coordenada(e);
    celdaCursor = [c, f];
    accionarCelda(c, f);
    mostrarJustificacion(c, f);
  });
  lienzo.addEventListener("mousemove", (e) => {
    if (estado) {
      mostrarJustificacion(...coordenada(e));
    }
  });
  lienzo.parentElement.addEventListener("mouseleave", () => {
    $("tooltip").hidden = true;
  });
  lienzo.addEventListener("keydown", (e) => {
    if (!estado || ocupado) {
      return;
    }
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", " "].includes(e.key)) {
      e.preventDefault();
      if (!celdaCursor) {
        const u = unidad();
        celdaCursor = u ? [u.col, u.fila] : [0, 0];
      }
      const [x, y] = celdaCursor;
      if (e.key === "Enter" || e.key === " ") {
        accionarCelda(x, y);
        return;
      }
      celdaCursor = [
        Math.max(0, Math.min(estado.mapa.ancho - 1, x + (e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0))),
        Math.max(0, Math.min(estado.mapa.alto - 1, y + (e.key === "ArrowUp" ? -1 : e.key === "ArrowDown" ? 1 : 0))),
      ];
      const v = estado.unidades.find((u) => u.col === celdaCursor[0] && u.fila === celdaCursor[1]);
      mensaje(
        `Casilla ${celdaCursor[0] + 1}, ${celdaCursor[1] + 1}: ${
          v
            ? `${v.id}, ${nombres[v.tipo]}, ${nombres[v.bando]}, vida ${v.vida}`
            : estado.mapa.terreno[celdaCursor[1]][celdaCursor[0]]
        }.`,
      );
      mostrarJustificacion(...celdaCursor);
    }
  });
  [
    ["¬", "Negación"],
    [" ∧ ", "Conjunción"],
    [" ∨ ", "Disyunción"],
    [" → ", "Implicación"],
    ["∀", "Para todo"],
    ["∃", "Existe"],
    [" = ", "Igualdad"],
    ["(", "Abrir paréntesis"],
    [")", "Cerrar paréntesis"],
    ["x", "Variable objetivo"],
    ["y", "Variable cuantificada"],
    ["yo", "Unidad atacante"],
  ].forEach(([texto, titulo]) => {
    const b = nodo("button", "", texto.trim());
    b.type = "button";
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    b.addEventListener("click", () => insertar(texto));
    $("teclado").append(b);
  });
  const predicados = {
    Mio: "Unidades del bando en turno",
    Enemigo: "Unidades rivales",
    Herido: "Vida inferior a la mitad",
    Infante: "Clase infante",
    Arquero: "Clase arquero",
    Medico: "Clase médico",
    Tanque: "Clase tanque",
    EnAgua: "Unidad sobre agua",
    Cerca: "Distancia de una casilla",
    Alineado: "Misma fila o columna",
  };
  // ------------------------ Botones del editor y acciones de la página

  Object.entries(predicados).forEach(([p, titulo]) => {
    const b = nodo("button", "", p);
    b.type = "button";
    b.title = titulo;
    b.addEventListener("click", () => insertar(`${p}(${p === "Cerca" || p === "Alineado" ? "x,y" : "x"})`));
    $("predicados").append(b);
  });
  document
    .querySelectorAll("[data-modo]")
    .forEach((b) => b.addEventListener("click", () => cambiarModo(b.dataset.modo)));
  ["azul", "rojo"].forEach((b) => $(`dificultad-${b}`).addEventListener("change", dificultad));
  $("nivel").addEventListener("change", describirNivel);
  $("iniciar").addEventListener("click", iniciarDesdeMenu);
  $("reintentar-niveles").addEventListener("click", cargarNiveles);
  $("ir-cpu").addEventListener("click", () => {
    volverMenu();
    cambiarModo("cpu");
    iniciarDesdeMenu();
  });
  $("formula").addEventListener("input", entradaFormula);
  $("abrir-editor").addEventListener("click", () => {
    editorAbierto = true;
    $("formula").focus();
    if (!$("formula").value) {
      $("formula").value = unidad()?.tipo === "Medico" ? "Mio(x)" : "Enemigo(x)";
    }
    programarPrevisualizacion();
  });
  $("atacar").addEventListener("click", () => {
    if (previsualizacion?.ok) {
      realizar("atacar", {
        atacante: seleccionado,
        formula: $("formula").value.trim(),
      });
    }
  });
  $("terminar-turno").addEventListener("click", () => realizar("terminar_turno"));
  $("abrir-menu").addEventListener("click", volverMenu);
  $("volver-menu").addEventListener("click", volverMenu);
  $("abrir-ayuda").addEventListener("click", () => $("ayuda").showModal());
  $("cerrar-ayuda").addEventListener("click", () => $("ayuda").close());
  $("continuar-turno").addEventListener("click", () => {
    $("relevo").close();
    lienzo.focus();
  });
  $("relevo").addEventListener("cancel", (e) => e.preventDefault());
  $("victoria").addEventListener("cancel", (e) => e.preventDefault());
  $("reintentar").addEventListener("click", () => iniciarPartida(configuracionAnterior));
  $("siguiente-nivel").addEventListener("click", () => {
    const i = niveles.findIndex((n) => String(n.id) === String(estado.nivel));
    if (niveles[i + 1]) {
      iniciarPartida({
        ...configuracionAnterior,
        nivel: niveles[i + 1].id,
      });
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(fotograma);
      fotograma = 0;
    } else {
      iniciarDibujo();
    }
  });
  arte.portada($("escena-menu"));
  cargarNiveles();
})();
