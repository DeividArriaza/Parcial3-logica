/* Arte original en matrices de píxeles. Sin recursos externos. */
"use strict";

window.ArteBatalla = (() => {
  // ------------------------ Sprites de las cuatro clases de unidad
  const matrices = {
    Infante: [
      "....hhhh....",
      "...hHHHHh...",
      "...ssssss...",
      "...skssk....",
      "....ssss....",
      "..bbbbbbbb..",
      ".bbBbbBbbbb.",
      ".sbBbbBbbsm.",
      "..bBBBBbb.m.",
      "...bbbbb..m.",
      "...ppppp....",
      "...pp.pp....",
      "...pp.pp....",
      "..ddd.ddd...",
    ],
    Arquero: [
      "....bbbb....",
      "...bBBBBb...",
      "...bssssb...",
      "...bskssb...",
      "....ssss..w.",
      "..bbbbbb.w.w",
      ".bbBbbbsww.w",
      ".sbBbbbbswww",
      "..bBBBBb.w.w",
      "...bbbbb..w.",
      "...ppppp....",
      "...pp.pp....",
      "...pp.pp....",
      "..ddd.ddd...",
    ],
    Medico: [
      "....wwww....",
      "...wwrwww...",
      "...wrrrww...",
      "...ssrss....",
      "...skssk....",
      "....ssss....",
      "..bbbbbbbb..",
      ".bbBbbBbbs..",
      ".sbBbbBbb.w.",
      "..bBBBBb.wrw",
      "...bbbbb..w.",
      "...pp.pp....",
      "...pp.pp....",
      "..ddd.ddd...",
    ],
    Tanque: [
      "...mmmmmm...",
      "..mMMMMMMm..",
      "..mMmmmmMm..",
      "..mmssssmm..",
      "...skssk....",
      "....ssss....",
      ".mmmmmmmmmm.",
      "mMmbbbbmmMMm",
      "mMmbBBbmmMMm",
      ".smBBBBmmms.",
      "..mmmmmmmm..",
      "..mmppppmm..",
      "...pp.pp....",
      "..ddd.ddd...",
    ],
  };
  // ------------------------ Matrices de terreno, de 16 por 16 píxeles

  const pasto = [
    "0000000000000000",
    "0000000000000000",
    "0010000000000000",
    "0101000000000000",
    "0000000000000000",
    "0000000000200000",
    "0000000000000000",
    "0000000000000000",
    "0000000000000000",
    "0000000000000000",
    "0000000010000000",
    "0000000101000000",
    "0000000000000000",
    "0000000000000000",
    "0002000000000000",
    "0000000000000000",
  ];
  const agua = [
    "0000000000000000",
    "0001111000000000",
    "0012222100000000",
    "0000000000000000",
    "0000000000000000",
    "0000000000111000",
    "0000000001222100",
    "0000000000000000",
    "0000000000000000",
    "0011100000000000",
    "0122210000000000",
    "0000000000000000",
    "0000000000000000",
    "0000000011110000",
    "0000000122221000",
    "0000000000000000",
  ];
  const muro = [
    "1111111111111111",
    "1222222122222221",
    "1233332123333321",
    "1233332123333321",
    "1222222122222221",
    "1111111111111111",
    "2221222222212222",
    "3331233333212333",
    "3331233333212333",
    "2221222222212222",
    "1111111111111111",
    "1222222122222221",
    "1233332123333321",
    "1233332123333321",
    "1222222122222221",
    "4444444444444444",
  ];
  // ------------------------ Dibujo de matrices y unidades

  function matriz(contexto, datos, paleta, x, y, escala) {
    datos.forEach((fila, j) =>
      [...fila].forEach((pixel, i) => {
        if (paleta[pixel]) {
          contexto.fillStyle = paleta[pixel];
          contexto.fillRect(
            Math.round(x + i * escala),
            Math.round(y + j * escala),
            Math.ceil(escala),
            Math.ceil(escala),
          );
        }
      }),
    );
  }

  function soldado(contexto, tipo, bando, x, y, escala = 3, opacidad = 1) {
    const azul = bando === "azul";
    contexto.save();
    contexto.globalAlpha *= opacidad;
    contexto.imageSmoothingEnabled = false;
    const paleta = {
      h: "#26353c",
      H: "#80949c",
      s: "#e9bf8b",
      k: "#302c2b",
      b: azul ? "#3189b8" : "#b44945",
      B: azul ? "#83d6e9" : "#ff9b7c",
      p: "#2d3a40",
      d: "#172a30",
      m: "#384950",
      M: "#8ea1a1",
      w: "#ebead4",
      r: "#e46e61",
    };
    contexto.fillStyle = "#142b2866";
    contexto.beginPath();
    contexto.ellipse(x + 6 * escala, y + 13.5 * escala, 6 * escala, 1.6 * escala, 0, 0, Math.PI * 2);
    contexto.fill();
    matriz(contexto, matrices[tipo] || matrices.Infante, paleta, x, y, escala);
    contexto.restore();
  }
  const baldosas = new Map();
  // ------------------------ Terreno y caché de baldosas

  function terreno(contexto, tipo, col, fila, tamano, tiempo = 0) {
    const variante = (col * 13 + fila * 7) % 4;
    const clave = `${tipo}-${variante}`;
    if (!baldosas.has(clave)) {
      const c = document.createElement("canvas");
      c.width = c.height = 16;
      const t = c.getContext("2d");
      const paleta =
        tipo === "agua"
          ? {
              0: "#386778",
              1: "#518f9b",
              2: "#75aeb2",
            }
          : tipo === "muro"
            ? {
                1: "#34433d",
                2: "#7e8771",
                3: "#959a80",
                4: "#293c33",
              }
            : {
                0: ["#527449", "#56784c", "#507147", "#54764a"][variante],
                1: "#789356",
                2: "#a3a46a",
              };
      matriz(t, tipo === "agua" ? agua : tipo === "muro" ? muro : pasto, paleta, 0, 0, 1);
      baldosas.set(clave, c);
    }
    contexto.drawImage(baldosas.get(clave), col * tamano, fila * tamano, tamano, tamano);
    if (tipo === "agua" && Math.floor(tiempo / 900 + col + fila) % 3 === 0) {
      contexto.fillStyle = "#a4d2cd44";
      contexto.fillRect(col * tamano + tamano * 0.2, fila * tamano + tamano * 0.38, tamano * 0.28, 2);
    }
  }
  // ------------------------ Retratos del escuadrón e ilustración del menú

  function retrato(unidad) {
    const c = document.createElement("canvas");
    c.width = 36;
    c.height = 42;
    c.setAttribute("aria-hidden", "true");
    soldado(c.getContext("2d"), unidad.tipo, unidad.bando, 0, 0, 3);
    return c;
  }

  function portada(lienzo) {
    const contexto = lienzo.getContext("2d");
    contexto.imageSmoothingEnabled = false;
    contexto.fillStyle = "#273b30";
    contexto.fillRect(0, 0, 640, 440);
    for (let f = 0; f < 10; f++) {
      for (let c = 0; c < 16; c++) {
        terreno(
          contexto,
          (c === 7 || c === 8) && f !== 4
            ? "agua"
            : (c === 4 && f > 1 && f < 4) || (c === 11 && f > 5 && f < 8)
              ? "muro"
              : "pasto",
          c,
          f,
          40,
        );
      }
    }
    [
      ["Infante", "azul", 3, 3],
      ["Arquero", "azul", 2, 5],
      ["Medico", "azul", 3, 7],
      ["Tanque", "azul", 5, 5],
      ["Infante", "rojo", 12, 3],
      ["Arquero", "rojo", 13, 5],
      ["Medico", "rojo", 12, 7],
      ["Tanque", "rojo", 10, 5],
    ].forEach(([t, b, c, f]) => soldado(contexto, t, b, c * 40 - 4, f * 40 - 13, 3));
    contexto.strokeStyle = "#d5ee89aa";
    contexto.setLineDash([5, 5]);
    contexto.lineWidth = 2;
    contexto.strokeRect(5 * 40 - 3, 5 * 40 - 3, 46, 46);
    contexto.setLineDash([]);
    contexto.fillStyle = "#142128";
    contexto.fillRect(0, 400, 640, 40);
    contexto.fillStyle = "#d5ee89";
    contexto.font = "14px Consolas,monospace";
    contexto.fillText("(Enemigo(x) ∧ Tanque(x))", 20, 426);
    contexto.fillStyle = "#91b0a2";
    contexto.fillText("→", 592, 426);
  }
  return {
    soldado,
    terreno,
    retrato,
    portada,
  };
})();
