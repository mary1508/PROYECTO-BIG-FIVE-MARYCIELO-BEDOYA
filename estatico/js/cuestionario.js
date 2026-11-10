// Progreso del cuestionario Likert y desplazamiento al primer ítem faltante.
(function () {
  const formulario = document.getElementById("formulario-likert");
  if (!formulario) return;
  const total = Number(formulario.dataset.total);
  const contador = document.getElementById("contador-respondidas");
  const barra = document.getElementById("barra-avance");
  const pista = document.getElementById("pista-avance");
  const estado = document.getElementById("estado-envio");

  function actualizar() {
    let respondidas = 0;
    for (let numero = 1; numero <= total; numero++) {
      if (formulario.querySelector(`input[name="item_${numero}"]:checked`)) respondidas++;
    }
    contador.textContent = respondidas;
    barra.style.width = (respondidas / total * 100) + "%";
    pista.setAttribute("aria-valuenow", respondidas);
    estado.textContent = respondidas === total
      ? "Todo respondido. Puedes continuar."
      : `Faltan ${total - respondidas} por responder.`;
  }

  formulario.addEventListener("change", (evento) => {
    const grupo = evento.target.closest(".pregunta");
    if (grupo) grupo.classList.remove("falta");
    actualizar();
  });

  formulario.addEventListener("submit", (evento) => {
    for (let numero = 1; numero <= total; numero++) {
      if (!formulario.querySelector(`input[name="item_${numero}"]:checked`)) {
        evento.preventDefault();
        const pregunta = document.getElementById(`pregunta-${numero}`);
        pregunta.classList.add("falta");
        pregunta.scrollIntoView({ behavior: "smooth", block: "center" });
        estado.textContent = `Falta responder la afirmación ${numero}.`;
        return;
      }
    }
  });

  const primerFaltante = document.querySelector(".pregunta.falta");
  if (primerFaltante) primerFaltante.scrollIntoView({ block: "center" });
  actualizar();
})();
