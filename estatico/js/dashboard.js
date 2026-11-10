// Dashboard: pide al servidor los resultados ya guardados (sin recalcular) y los dibuja.
(function () {
  const COLORES = {
    apertura: "#7a4fb0", responsabilidad: "#0f5c6e", extraversion: "#d4780f",
    amabilidad: "#2e8b57", neuroticismo: "#b3425c",
  };
  const PALETA = ["#0f5c6e", "#d4780f", "#7a4fb0", "#2e8b57", "#b3425c", "#4b6a88"];
  const graficos = {};
  let datos = null;

  const filtros = document.getElementById("filtros");
  const tablero = document.getElementById("tablero");
  const avisos = document.getElementById("avisos");

  const formato = (n, d = 3) => Number(n).toLocaleString("es-PE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const formatoP = (p) => (p < 0.001 ? "< 0,001" : formato(p, 3));
  const escapar = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const aclarar = (hex) => hex + "55";

  function dibujar(id, configuracion) {
    if (graficos[id]) graficos[id].destroy();
    graficos[id] = new Chart(document.getElementById(id), configuracion);
  }

  const baseOpciones = { responsive: true, maintainAspectRatio: false, animation: { duration: 250 } };

  async function cargar() {
    const parametros = new URLSearchParams(new FormData(filtros));
    tablero.classList.add("cargando");
    try {
      const respuesta = await fetch("/admin/api/dashboard?" + parametros, { headers: { Accept: "application/json" } });
      if (!respuesta.ok) throw new Error();
      datos = await respuesta.json();
      pintar();
    } catch (e) {
      avisos.innerHTML = '<div class="mensaje error" role="alert">No se pudieron cargar los resultados. Recarga la página; si el problema continúa, inicia sesión nuevamente.</div>';
    } finally {
      tablero.classList.remove("cargando");
    }
  }

  function pintar() {
    const { analisis, correlaciones, subgrupos, frecuencias, medias_grupo, descriptivo_global, dispersion } = datos;
    document.getElementById("nombre-variable").textContent = datos.variable_nombre.toLowerCase();

    avisos.innerHTML = analisis.estado !== "completo"
      ? '<div class="mensaje aviso" role="status"><strong>Muestra insuficiente.</strong> Solo se muestra la estadística descriptiva; amplía la muestra para ver correlaciones y comparaciones.</div>'
      : "";
    if (analisis.advertencias.length) {
      avisos.innerHTML += '<div class="mensaje info"><strong>Notas del análisis</strong><ul>' +
        analisis.advertencias.map((a) => `<li>${escapar(a)}</li>`).join("") + "</ul></div>";
    }

    const significativas = correlaciones.filter((c) => c.significativo).length;
    document.getElementById("indicadores").innerHTML = [
      [analisis.n, "Participantes emparejados"],
      [significativas + " de " + correlaciones.length, "Correlaciones significativas"],
      [subgrupos.filter((s) => s.significativo).length + " de " + subgrupos.length, "Diferencias entre subgrupos significativas"],
      [analisis.fecha, "Fecha del análisis"],
    ].map(([valor, nombre], i) => `<div class="tarjeta indicador"><div class="valor" style="${i === 3 ? "font-size:1.15rem;padding-top:10px" : ""}">${escapar(valor)}</div><div class="nombre">${nombre}</div></div>`).join("");

    // Correlaciones
    dibujar("grafico-correlaciones", {
      type: "bar",
      data: {
        labels: correlaciones.map((c) => c.etiqueta),
        datasets: [{
          label: "Coeficiente de correlación",
          data: correlaciones.map((c) => c.coeficiente),
          backgroundColor: correlaciones.map((c) => (c.significativo ? COLORES[c.dimension] : aclarar(COLORES[c.dimension]))),
          borderColor: correlaciones.map((c) => COLORES[c.dimension]), borderWidth: 1.5, borderRadius: 4,
        }],
      },
      options: {
        ...baseOpciones, plugins: { legend: { display: false }, tooltip: { callbacks: {
          label: (ctx) => { const c = correlaciones[ctx.dataIndex]; return `${c.prueba}: r = ${formato(c.coeficiente)}, p = ${formatoP(c.p_valor)}`; } } } },
        scales: { y: { min: -1, max: 1, title: { display: true, text: "Coeficiente" } } },
      },
    });
    document.getElementById("tabla-correlaciones").innerHTML = correlaciones.length
      ? "<thead><tr><th>Dimensión</th><th>Prueba</th><th class='numero'>Coeficiente</th><th class='numero'>p</th><th class='numero'>n</th><th>Resultado</th></tr></thead><tbody>" +
        correlaciones.map((c) => `<tr class="${c.significativo ? "significativo" : ""}"><td>${escapar(c.etiqueta)}</td><td>${c.prueba}</td><td class="numero">${formato(c.coeficiente)}</td><td class="numero">${formatoP(c.p_valor)}</td><td class="numero">${c.n}</td><td>${c.significativo ? '<span class="etiqueta aviso">Significativo</span>' : '<span class="etiqueta">No significativo</span>'}</td></tr>`).join("") + "</tbody>"
      : "<tbody><tr><td class='vacio'>Sin correlaciones para mostrar con estos filtros o con muestra insuficiente.</td></tr></tbody>";

    // Dispersión (solo con una dimensión seleccionada)
    const tarjetaDispersion = document.getElementById("tarjeta-dispersion");
    tarjetaDispersion.hidden = !dispersion.length;
    if (dispersion.length) {
      const dimension = filtros.dimension.value;
      document.getElementById("titulo-dispersion").textContent = `${datos.etiqueta_x} vs. ${datos.variable_nombre.toLowerCase()}`;
      dibujar("grafico-dispersion", {
        type: "scatter",
        data: { datasets: [{ label: "Participantes", data: dispersion, backgroundColor: COLORES[dimension] + "aa", pointRadius: 5 }] },
        options: { ...baseOpciones, plugins: { legend: { display: false } },
          scales: { x: { title: { display: true, text: datos.etiqueta_x } }, y: { title: { display: true, text: datos.variable_nombre } } } },
      });
    }

    pintarGrupos();

    // Frecuencias
    [["rol", "grafico-frec-rol"], ["experiencia", "grafico-frec-experiencia"], ["metodologia", "grafico-frec-metodologia"]].forEach(([clave, id]) => {
      const filas = frecuencias[clave];
      dibujar(id, {
        type: "doughnut",
        data: { labels: filas.map((f) => f.categoria), datasets: [{ data: filas.map((f) => f.n), backgroundColor: PALETA, borderWidth: 2 }] },
        options: { ...baseOpciones, cutout: "58%", plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } } },
      });
    });

    // Subgrupos
    document.getElementById("tabla-subgrupos").innerHTML = subgrupos.length
      ? "<thead><tr><th>Agrupación</th><th>Variable</th><th>Prueba</th><th class='numero'>Estadístico</th><th class='numero'>p</th><th class='numero'>Grupos</th><th>Excluidos (n bajo)</th></tr></thead><tbody>" +
        subgrupos.map((s) => `<tr class="${s.significativo ? "significativo" : ""}"><td>${s.agrupacion === "rol" ? "Rol" : "Experiencia"}</td><td>${escapar(s.variable)}</td><td>${s.prueba}</td><td class="numero">${formato(s.estadistico)}</td><td class="numero">${formatoP(s.p_valor)}</td><td class="numero">${s.grupos}</td><td>${escapar(s.excluidos || "—")}</td></tr>`).join("") + "</tbody>"
      : "<tbody><tr><td class='vacio'>No hay comparaciones por subgrupo para mostrar.</td></tr></tbody>";

    // Descriptiva global
    document.getElementById("tabla-descriptiva").innerHTML =
      "<thead><tr><th>Variable</th><th class='numero'>Media</th><th class='numero'>Desv. estándar</th><th class='numero'>n</th></tr></thead><tbody>" +
      descriptivo_global.map((d) => `<tr><td>${escapar(d.variable)}</td><td class="numero">${formato(d.media)}</td><td class="numero">${formato(d.desviacion)}</td><td class="numero">${d.n}</td></tr>`).join("") + "</tbody>";
  }

  function pintarGrupos() {
    if (!datos) return;
    const agrupacion = document.getElementById("agrupar-por").value;
    const filas = datos.medias_grupo[agrupacion];
    const categorias = [...new Set(filas.map((f) => f.categoria))];
    const variables = [...new Set(filas.map((f) => f.variable))];
    const clavePorEtiqueta = { "Apertura a la experiencia": "apertura", "Responsabilidad": "responsabilidad", "Extraversión": "extraversion", "Amabilidad": "amabilidad", "Neuroticismo": "neuroticismo" };
    dibujar("grafico-grupos", {
      type: "bar",
      data: {
        labels: categorias,
        datasets: variables.map((variable) => ({
          label: variable, backgroundColor: COLORES[clavePorEtiqueta[variable]], borderRadius: 3,
          data: categorias.map((c) => { const f = filas.find((x) => x.categoria === c && x.variable === variable); return f ? f.media : null; }),
        })),
      },
      options: { ...baseOpciones, plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } }, scales: { y: { min: 1, max: 5 } } },
    });
  }

  filtros.addEventListener("change", cargar);
  filtros.addEventListener("reset", () => setTimeout(cargar, 0));
  document.getElementById("agrupar-por").addEventListener("change", pintarGrupos);
  document.getElementById("boton-pdf")?.addEventListener("click", () => window.print());
  document.querySelectorAll("[data-exportar]").forEach((boton) => boton.addEventListener("click", () => {
    const lienzo = document.getElementById(boton.dataset.exportar);
    const temporal = document.createElement("canvas");
    temporal.width = lienzo.width; temporal.height = lienzo.height;
    const contexto = temporal.getContext("2d");
    contexto.fillStyle = "#ffffff"; contexto.fillRect(0, 0, temporal.width, temporal.height);
    contexto.drawImage(lienzo, 0, 0);
    const enlace = document.createElement("a");
    enlace.download = boton.dataset.exportar + ".png"; enlace.href = temporal.toDataURL("image/png"); enlace.click();
  }));

  cargar();
})();
