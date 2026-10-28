"use strict";

// El instructor coordina la enseñanza. Toda evaluación sigue ocurriendo en la API.
window.InstructorBatalla = (() => {
  const $ = (id) => document.getElementById(id);
  const CLAVE_PROGRESO = "batalla-logica.lecciones.v1";
  const nombresPaso = {
    explicacion: "Vamos a descubrirlo",
    ejemplo: "Lo hacemos juntos",
    practica: "Ahora prueba tú",
    reto: "Tu turno de demostrarlo",
  };

  function elemento(etiqueta, texto, clase = "") {
    const nodo = document.createElement(etiqueta);
    nodo.textContent = texto;
    nodo.className = clase;
    return nodo;
  }

  // Un almacenamiento bloqueado no impide seguir aprendiendo.
  function leerProgreso() {
    try {
      const datos = JSON.parse(localStorage.getItem(CLAVE_PROGRESO) || "[]");
      return new Set(Array.isArray(datos) ? datos.map(String) : []);
    } catch {
      return new Set();
    }
  }

  function guardarLeccion(id) {
    const completadas = leerProgreso();
    completadas.add(String(id));
    try {
      localStorage.setItem(CLAVE_PROGRESO, JSON.stringify([...completadas]));
    } catch {
      // Se conserva la celebración aunque el navegador no permita guardar.
    }
  }

  // Conserva la razón decisiva y evita mostrar todo el árbol de evaluación.
  function razonSencilla(arbol) {
    if (!arbol) return "El servidor no devolvió una justificación para esta unidad.";
    const pendientes = [arbol];
    while (pendientes.length) {
      const paso = pendientes.shift();
      if (["testigo", "contraejemplo"].includes(paso.tipo) && paso.explicacion) {
        return paso.explicacion;
      }
      pendientes.push(...(paso.hijos || []));
    }
    return arbol.explicacion || arbol.formula || "";
  }
  class Instructor {
    constructor(puente) {
      this.puente = puente;
      this.activo = false;
      this.indice = 0;
      this.generacion = 0;
      this.procesando = false;
      this.escribiendo = false;
      this.marcas = new Map();
      this.registros = new Map();
      this.destinoEditor = $("editor").parentElement;
      this.burbujas = elemento("div", "", "burbujas-tutorial");
      $("tablero").parentElement.append(this.burbujas);
      $("instructor-anterior").addEventListener("click", () => this.cambiarPaso(this.indice - 1));
      $("instructor-siguiente").addEventListener("click", () => this.cambiarPaso(this.indice + 1));
      $("instructor-comprobar").addEventListener("click", () => this.comprobar());
      $("instructor-pista").addEventListener("click", () => this.revelarPista());
      $("instructor-respuesta").addEventListener("click", () => this.verRespuesta());
      $("instructor-reintentar").addEventListener("click", () => this.puente.reiniciar(this.indice));
      $("formula").addEventListener("input", () => this.formulaEditada());
    }

    get paso() {
      return this.leccion?.pasos?.[this.indice];
    }

    get registro() {
      if (!this.registros.has(this.indice)) {
        this.registros.set(this.indice, { resuelto: false, respuestaVista: false, pistas: 0 });
      }
      return this.registros.get(this.indice);
    }

    get atacante() {
      return (
        this.paso?.atacante ||
        this.leccion.atacante ||
        this.puente.estado().unidades.find((unidad) => unidad.bando === this.puente.estado().turno)?.id
      );
    }

    get permiteAtaque() {
      return !this.activo || (this.paso?.tipo === "reto" && !this.fallo && !this.procesando);
    }

    // Los metadatos pueden venir completos en niveles o en la ruta de detalle.
    async iniciar(leccion, estado, indice = 0) {
      this.detener();
      if (estado.modo !== "tutorial") return;
      if (!leccion?.pasos?.length) {
        const detalle = await this.puente.consultar(`nivel/${estado.nivel}`);
        leccion = detalle.nivel || detalle.leccion;
      }
      if (!leccion?.pasos?.length) {
        throw new Error("Esta lección todavía no tiene pasos guiados disponibles en el servidor.");
      }
      this.leccion = leccion;
      this.unidadesIniciales = structuredClone(estado.unidades);
      this.activo = true;
      this.registros = new Map();
      this.fallo = false;
      this.completada = false;
      document.body.classList.add("tutorial-guiado");
      $("instructor").hidden = false;
      $("panel-tutorial").hidden = true;
      await this.cambiarPaso(indice, true);
    }

    detener() {
      this.generacion++;
      this.controlPeticion?.abort();
      this.activo = false;
      this.escribiendo = false;
      this.procesando = false;
      this.marcas.clear();
      this.burbujas.replaceChildren();
      $("instructor").hidden = true;
      $("editor").hidden = false;
      this.destinoEditor.append($("editor"));
      $("atacar").hidden = false;
      document.querySelectorAll("#teclado button, #predicados button").forEach((boton) => {
        boton.hidden = false;
      });
      document.body.classList.remove("tutorial-guiado");
    }

    async cambiarPaso(indice, inicial = false) {
      if (!this.activo || (!inicial && (this.puente.ocupado() || this.procesando))) return;
      if (indice < 0 || indice >= this.leccion.pasos.length) return;
      if (
        !inicial &&
        indice > this.indice &&
        this.paso?.tipo === "practica" &&
        !this.registro.resuelto &&
        !this.registro.respuestaVista
      )
        return;
      if (!inicial && ["practica", "reto"].includes(this.paso?.tipo)) {
        this.registro.formula = $("formula").value;
      }
      this.controlPeticion?.abort();
      this.controlPeticion = new AbortController();
      const generacion = ++this.generacion;
      this.indice = indice;
      this.marcas.clear();
      this.burbujas.replaceChildren();
      this.procesando = false;
      this.escribiendo = false;
      // Cada ejemplo, práctica o reto puede traer su propio mundo desde la API.
      if (this.paso.estado) this.puente.cambiarEscenario(this.paso.estado);
      this.unidadesIniciales = structuredClone(this.puente.estado().unidades);
      this.mostrarPaso();
      if (!inicial) $("instructor-titulo").focus({ preventScroll: true });
      const paso = this.paso;
      const formula = this.registro.formula ?? (paso.tipo === "practica" ? paso.plantilla || "" : "");
      this.puente.preparar(formula, this.atacante);
      for (const id of paso.resaltar || []) this.marcas.set(id, "atencion");
      if (paso.tipo === "ejemplo") await this.mostrarEjemplo(generacion);
      this.actualizarControles();
    }

    // El panel conserva los mismos controles entre pasos para no perder el foco.
    mostrarPaso() {
      const paso = this.paso;
      const editable = ["practica", "reto"].includes(paso.tipo);
      if (editable) $("instructor").insertBefore($("editor"), $("instructor-feedback"));
      else this.destinoEditor.append($("editor"));
      $("indicacion-tablero").textContent =
        paso.tipo === "explicacion"
          ? "Las flechas señalan las unidades de la explicación"
          : "Atacante de esta lección: " + this.atacante;
      $("instructor-leccion").textContent = `${this.leccion.id} · ${this.leccion.titulo}`;
      $("instructor-contador").textContent = `${this.indice + 1} / ${this.leccion.pasos.length}`;
      $("instructor-progreso").max = this.leccion.pasos.length;
      $("instructor-progreso").value = this.indice + 1;
      $("instructor-etapas").replaceChildren();
      this.leccion.pasos.forEach((p, i) => {
        const practicas = this.leccion.pasos.filter((paso) => paso.tipo === "practica").length;
        const numero = this.leccion.pasos.slice(0, i + 1).filter((paso) => paso.tipo === "practica").length;
        const item = elemento(
          "li",
          p.tipo === "practica" && practicas > 1
            ? `Práctica ${numero}/${practicas}`
            : { explicacion: "Descubre", ejemplo: "Observa", practica: "Practica", reto: "Reto" }[p.tipo],
        );
        if (i === this.indice) item.setAttribute("aria-current", "step");
        if (i < this.indice) item.classList.add("visitado");
        $("instructor-etapas").append(item);
      });
      $("instructor-tipo").textContent = nombresPaso[paso.tipo] || "Paso de la lección";
      $("instructor-titulo").textContent = paso.titulo || nombresPaso[paso.tipo];
      const textos = {
        ejemplo: "Mira la fórmula. Revisaremos cada soldado y veremos por qué entra o queda fuera del ataque.",
        practica: "Completa los huecos ___ en el editor y pulsa Comprobar. Puedes probar sin gastar energía.",
        reto: "Ahora escribe tu propia fórmula. Esta vez lanzarás un ataque real: elige exactamente los objetivos.",
      };
      $("instructor-texto").textContent = paso.texto || textos[paso.tipo] || "";
      $("instructor-ejemplo").hidden = paso.tipo !== "ejemplo";
      $("instructor-formula").textContent = "";
      $("instructor-lectura").textContent = "";
      $("instructor-comentarios").replaceChildren();
      $("instructor-feedback").hidden = true;
      $("instructor-pistas").replaceChildren();
      $("instructor-objetivo").hidden = !["practica", "reto"].includes(paso.tipo);
      const objetivos = paso.objetivo;
      $("instructor-objetivo").textContent = Array.isArray(objetivos)
        ? `Tu objetivo: incluye exactamente a ${objetivos.join(", ")}.`
        : objetivos || this.leccion.objetivo || "";
      $("editor").hidden = !["practica", "reto"].includes(paso.tipo);
      $("atacar").hidden = paso.tipo !== "reto";
      $("instructor-comprobar").hidden = paso.tipo !== "practica";
      $("instructor-pista").hidden = !["practica", "reto"].includes(paso.tipo);
      $("instructor-respuesta").hidden = paso.tipo !== "practica";
      $("instructor-reintentar").hidden = paso.tipo !== "reto" || !this.fallo;
      this.mostrarSimbolo(paso.simbolo);
      this.mostrarTabla(paso.tabla_verdad || (paso.tipo === "explicacion" && this.leccion.tabla_verdad));
      for (let i = 0; i < this.registro.pistas; i++) this.agregarPista(i);
      if (this.registro.resuelto)
        this.mostrarFeedback({ acierto: true, mensaje: "¡Bien! Ya resolviste esta práctica." });
      else if (this.registro.respuestaVista) {
        this.mostrarFeedback({ acierto: true, mensaje: "Respuesta revelada. Léela con calma; ya puedes continuar." });
      }
    }

    mostrarSimbolo(dato) {
      const tarjeta = $("instructor-simbolo");
      tarjeta.replaceChildren();
      tarjeta.hidden = !dato;
      if (!dato) return;
      const signo = typeof dato === "string" ? dato : dato.simbolo || dato.signo;
      tarjeta.append(elemento("strong", signo, "signo-grande"));
      const explicacion = elemento("div", "");
      if (dato.nombre) explicacion.append(elemento("strong", dato.nombre));
      if (dato.lectura) explicacion.append(elemento("p", `Se lee: ${dato.lectura}`));
      if (dato.teclado || dato.atajo) {
        explicacion.append(elemento("small", `En el teclado: ${dato.teclado || dato.atajo}`));
      }
      tarjeta.append(explicacion);
    }

    mostrarTabla(filas) {
      const contenedor = $("instructor-tabla");
      contenedor.hidden = !Array.isArray(filas);
      contenedor.replaceChildren();
      if (!Array.isArray(filas)) return;
      const tabla = elemento("table", "", "tabla-verdad");
      tabla.append(elemento("caption", this.paso.tabla_titulo || this.leccion.tabla_titulo || "Tabla de verdad"));
      const encabezado = elemento("tr", "");
      ["P", "Q", "P → Q"].forEach((nombre) => {
        const celda = elemento("th", nombre);
        celda.scope = "col";
        encabezado.append(celda);
      });
      const cabeza = elemento("thead", "");
      cabeza.append(encabezado);
      const cuerpo = elemento("tbody", "");
      filas.forEach((fila) => {
        const renglon = elemento("tr", "");
        [fila.antecedente, fila.consecuente, fila.resultado].forEach((v) => {
          renglon.append(elemento("td", v ? "Verdadero" : "Falso"));
        });
        cuerpo.append(renglon);
      });
      tabla.append(cabeza, cuerpo);
      contenedor.append(tabla);
    }

    // La generación invalida el tecleo y las peticiones al cambiar de pantalla.
    async mostrarEjemplo(generacion) {
      this.escribiendo = true;
      this.actualizarControles();
      const formula = this.paso.formula || "";
      const reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;
      for (let i = reducir ? formula.length : 1; i <= formula.length; i++) {
        if (generacion !== this.generacion) return;
        $("instructor-formula").textContent = formula.slice(0, i);
        if (!reducir) await new Promise((resolver) => setTimeout(resolver, 24));
      }
      if (generacion !== this.generacion) return;
      this.escribiendo = false;
      this.procesando = true;
      this.puente.preparar(formula, this.atacante);
      try {
        const respuesta = await this.puente.consultar(
          "previsualizar",
          {
            estado: this.puente.estado(),
            atacante: this.atacante,
            formula,
          },
          this.controlPeticion.signal,
        );
        if (generacion !== this.generacion) return;
        this.puente.mostrarPrevisualizacion(respuesta);
        $("instructor-lectura").textContent = respuesta.lectura || this.paso.lectura || "";
        this.mostrarComentarios(respuesta.objetivos || []);
      } catch (error) {
        if (generacion === this.generacion && error.name !== "AbortError") {
          this.mostrarFeedback({ mensaje: error.message });
        }
      } finally {
        if (generacion === this.generacion) {
          this.procesando = false;
          this.actualizarControles();
        }
      }
    }

    mostrarComentarios(objetivos) {
      $("instructor-comentarios").replaceChildren();
      this.burbujas.replaceChildren();
      for (const id of (this.paso.comentar || []).slice(0, 2)) {
        const objetivo = objetivos.find((o) => o.id === id);
        const unidad = this.unidadesIniciales.find((u) => u.id === id);
        if (!objetivo || !unidad) continue;
        const alcanza = objetivo.cumple && objetivo.en_alcance;
        const razon = !objetivo.en_alcance
          ? "Está fuera del alcance del atacante: puede servir de testigo, pero no recibe el ataque."
          : razonSencilla(objetivo.arbol);
        const tarjeta = elemento("div", "", "comentario-unidad");
        tarjeta.append(elemento("strong", `${id} · ${alcanza ? "Sí entra" : "Queda fuera"}`), elemento("p", razon));
        $("instructor-comentarios").append(tarjeta);
        const burbuja = elemento("div", `${id}: ${razon}`, "burbuja-unidad");
        burbuja.style.left = `${Math.min(64, Math.max(2, (unidad.col / this.puente.estado().mapa.ancho) * 100))}%`;
        burbuja.style.top = `${id === this.paso.comentar[0] ? 4 : 76}%`;
        this.burbujas.append(burbuja);
      }
    }

    async comprobar() {
      if (!this.activo || this.paso.tipo !== "practica" || this.procesando || this.puente.ocupado()) return;
      const generacion = this.generacion;
      this.procesando = true;
      this.actualizarControles();
      try {
        const respuesta = await this.puente.consultar(
          "practicar",
          {
            estado: this.puente.estado(),
            nivel: this.leccion.id,
            paso: this.indice,
            formula: $("formula").value.trim(),
          },
          this.controlPeticion.signal,
        );
        if (generacion !== this.generacion) return;
        this.registro.resuelto = respuesta.acierto === true;
        this.registro.formula = $("formula").value;
        this.mostrarFeedback(respuesta);
        if (respuesta.lectura) this.puente.mostrarLectura(respuesta.lectura);
      } catch (error) {
        if (generacion !== this.generacion || error.name === "AbortError") return;
        this.mostrarFeedback({ mensaje: error.message });
      } finally {
        if (generacion === this.generacion) {
          this.procesando = false;
          this.actualizarControles();
        }
      }
    }

    formulaEditada() {
      if (!this.activo || !["practica", "reto"].includes(this.paso.tipo)) return;
      this.registro.resuelto = false;
      this.registro.respuestaVista = false;
      this.registro.formula = $("formula").value;
      this.marcas.clear();
      $("instructor-feedback").hidden = true;
      this.actualizarControles();
    }

    mostrarFeedback(respuesta) {
      const panel = $("instructor-feedback");
      panel.hidden = false;
      panel.classList.toggle("acierto", respuesta.acierto === true);
      panel.replaceChildren(elemento("strong", respuesta.acierto ? "¡Lo tienes!" : "Vamos a revisarlo"));
      panel.append(elemento("p", respuesta.mensaje || "Compara los soldados elegidos con tu objetivo."));
      this.marcas.clear();
      for (const id of respuesta.sobran || []) this.marcas.set(id, "sobra");
      for (const id of respuesta.faltan || []) this.marcas.set(id, "falta");
      if (respuesta.sobran?.length)
        panel.append(elemento("p", `Sobran: ${respuesta.sobran.join(", ")} · marca roja ×.`));
      if (respuesta.faltan?.length)
        panel.append(elemento("p", `Faltan: ${respuesta.faltan.join(", ")} · marca amarilla +.`));
      if (respuesta.acierto) {
        for (const id of respuesta.golpea || []) this.marcas.set(id, "correcto");
      }
    }

    pistasDisponibles() {
      return this.paso.pistas || [];
    }

    agregarPista(indice) {
      const pista = this.pistasDisponibles()[indice];
      if (pista) $("instructor-pistas").append(elemento("li", typeof pista === "string" ? pista : pista.texto));
    }

    revelarPista() {
      if (this.procesando || this.puente.ocupado()) return;
      if (this.registro.pistas < this.pistasDisponibles().length) {
        this.agregarPista(this.registro.pistas++);
      }
      this.actualizarControles();
    }

    verRespuesta() {
      if (this.procesando || this.puente.ocupado()) return;
      const formula = this.paso.solucion || this.paso.respuesta;
      if (!formula) return;
      this.registro.respuestaVista = true;
      this.registro.formula = formula;
      this.puente.preparar(formula, this.atacante);
      this.mostrarFeedback({ acierto: true, mensaje: "Esta es la respuesta. Léela en español antes de continuar." });
      this.actualizarControles();
    }

    observarResultado(respuesta) {
      if (!this.activo || this.paso.tipo !== "reto") return;
      const estado = respuesta.estado;
      this.completada = !!(estado.nivel_completado || estado.ganador === "azul");
      this.fallo = !this.completada;
      if (this.completada) guardarLeccion(this.leccion.id);
      this.mostrarFeedback({
        acierto: this.completada,
        mensaje:
          respuesta.mensaje ||
          estado.mensaje_nivel ||
          (this.completada
            ? "Elegiste exactamente a los soldados del objetivo. ¡Buen trabajo!"
            : "El ataque no eligió el grupo exacto. Reintenta el reto con el tablero original."),
        sobran: respuesta.sobran || estado.sobran || [],
        faltan: respuesta.faltan || estado.faltan || [],
      });
      $("instructor-reintentar").hidden = !this.fallo;
      this.actualizarControles();
    }

    actualizarControles(ocupado = this.puente.ocupado()) {
      if (!this.activo) return;
      const bloqueado = ocupado || this.procesando || this.escribiendo;
      $("instructor-anterior").disabled = bloqueado || this.indice === 0 || this.fallo || this.completada;
      $("instructor-siguiente").hidden = this.paso.tipo === "reto";
      $("instructor-siguiente").disabled =
        bloqueado || (this.paso.tipo === "practica" && !this.registro.resuelto && !this.registro.respuestaVista);
      $("instructor-comprobar").disabled = bloqueado || !$("formula").value.trim();
      $("instructor-pista").disabled = bloqueado || this.registro.pistas >= this.pistasDisponibles().length;
      $("instructor-respuesta").disabled = bloqueado || !(this.paso.solucion || this.paso.respuesta);
      $("instructor-reintentar").disabled = bloqueado;
      $("formula").disabled = bloqueado || this.fallo || this.completada;
      document.querySelectorAll("#teclado button, #predicados button").forEach((boton) => {
        boton.disabled = bloqueado || this.fallo || this.completada;
      });
      const permitidos = new Set(this.leccion.simbolos || []);
      document.querySelectorAll("#predicados button").forEach((boton) => {
        boton.hidden = !permitidos.has(boton.textContent);
      });
      document.querySelectorAll("#teclado button").forEach((boton) => {
        const simbolo = boton.textContent;
        boton.hidden = ["¬", "∧", "∨", "→", "∀", "∃", "=", "yo"].includes(simbolo) && !permitidos.has(simbolo);
      });
      if (!this.permiteAtaque) $("atacar").disabled = true;
    }

    // Las marcas usan las posiciones iniciales, incluso si un fallo eliminó una unidad.
    dibujar(contexto, tamano, tiempo) {
      if (!this.activo) return;
      const reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;
      for (const [id, marca] of this.marcas) {
        const unidad = this.unidadesIniciales.find((u) => u.id === id);
        if (!unidad) continue;
        const x = unidad.col * tamano;
        const y = unidad.fila * tamano;
        const colores = { atencion: "#ddf59b", sobra: "#ff8b7c", falta: "#ffdb75", correcto: "#a8eebc" };
        contexto.save();
        contexto.strokeStyle = colores[marca];
        contexto.fillStyle = colores[marca];
        contexto.lineWidth = 3;
        contexto.globalAlpha = reducir ? 1 : 0.65 + Math.sin(tiempo / 250) * 0.25;
        contexto.strokeRect(x + 4, y + 4, tamano - 8, tamano - 8);
        contexto.globalAlpha = 1;
        contexto.font = "bold 24px Consolas,monospace";
        contexto.fillText({ sobra: "×", falta: "+", correcto: "✓", atencion: "↓" }[marca], x + 55, y + 27);
        contexto.restore();
      }
    }
  }

  return { Instructor, leerProgreso, guardarLeccion };
})();
