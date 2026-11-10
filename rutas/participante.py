"""Rutas públicas del participante (CU1 y CU2). Acceso abierto por enlace, sin credenciales."""
from flask import Blueprint, redirect, render_template, request, session, url_for

from modelos import Empresa, Participante, ROLES, bd
from servicios import formulario as servicio
from servicios.instrumentos import (
    ITEMS_BFI44, ITEMS_ESCALA_RENDIMIENTO, OPCIONES_LIKERT, TOTAL_ITEMS_BFI, TOTAL_ITEMS_ESCALA,
)

plano_participante = Blueprint("participante", __name__)


def participante_actual() -> Participante | None:
    codigo = session.get("codigo_anonimo")
    return bd.session.get(Participante, codigo) if codigo else None


@plano_participante.route("/")
def bienvenida():
    return render_template("participante/bienvenida.html")


@plano_participante.route("/iniciar", methods=["POST"])
def iniciar():
    if request.form.get("consentimiento") != "si":
        return render_template("participante/bienvenida.html",
                               error="Para continuar debe aceptar el consentimiento informado."), 400
    session["consentimiento"] = True
    return redirect(url_for("participante.perfil"))


@plano_participante.route("/perfil", methods=["GET", "POST"])
def perfil():
    if not session.get("consentimiento"):
        return redirect(url_for("participante.bienvenida"))
    if participante_actual():
        return redirect(url_for("participante.bfi"))
    empresas = Empresa.query.order_by(Empresa.nombre).all()
    contexto = {"empresas": empresas, "roles": ROLES, "errores": [], "datos": request.form}
    if request.method == "POST":
        datos, errores = servicio.validar_perfil(request.form.get("id_equipo"), request.form.get("rol"),
                                                 request.form.get("anios_experiencia"))
        if errores:
            contexto["errores"] = errores
            return render_template("participante/perfil.html", **contexto), 400
        participante = servicio.registrar_participante(datos["equipo"], datos["rol"], datos["anios"])
        session["codigo_anonimo"] = participante.codigo_anonimo
        return redirect(url_for("participante.bfi"))
    return render_template("participante/perfil.html", **contexto)


def _redirigir_segun_estado(participante: Participante | None, requerido: str):
    """Devuelve una redirección si el participante no está en el paso correcto."""
    if participante is None:
        return redirect(url_for("participante.bienvenida"))
    if participante.estado_formulario == "completo":
        return redirect(url_for("participante.gracias"))
    if requerido == "bfi" and participante.estado_formulario == "bfi_completo":
        return redirect(url_for("participante.escala"))
    if requerido == "escala" and participante.estado_formulario == "en_progreso":
        return redirect(url_for("participante.bfi"))
    return None


@plano_participante.route("/cuestionario", methods=["GET", "POST"])
def bfi():
    participante = participante_actual()
    desvio = _redirigir_segun_estado(participante, "bfi")
    if desvio:
        return desvio
    respuestas, faltantes = {}, []
    if request.method == "POST":
        respuestas, faltantes = servicio.leer_respuestas(request.form, "item", TOTAL_ITEMS_BFI)
        if not faltantes:
            servicio.guardar_bfi44(participante, respuestas)
            return redirect(url_for("participante.escala"))
    return render_template("participante/bfi44.html", items=ITEMS_BFI44, opciones=OPCIONES_LIKERT,
                           respuestas=respuestas, faltantes=faltantes, codigo=participante.codigo_anonimo,
                           total=TOTAL_ITEMS_BFI), (400 if faltantes else 200)


@plano_participante.route("/escala-rendimiento", methods=["GET", "POST"])
def escala():
    participante = participante_actual()
    desvio = _redirigir_segun_estado(participante, "escala")
    if desvio:
        return desvio
    respuestas, faltantes = {}, []
    if request.method == "POST":
        respuestas, faltantes = servicio.leer_respuestas(request.form, "item", TOTAL_ITEMS_ESCALA)
        if not faltantes:
            servicio.guardar_escala_y_finalizar(participante, respuestas)
            return redirect(url_for("participante.gracias"))
    return render_template("participante/escala.html", items=ITEMS_ESCALA_RENDIMIENTO, opciones=OPCIONES_LIKERT,
                           respuestas=respuestas, faltantes=faltantes, codigo=participante.codigo_anonimo,
                           total=TOTAL_ITEMS_ESCALA), (400 if faltantes else 200)


@plano_participante.route("/gracias")
def gracias():
    participante = participante_actual()
    if participante is None or not participante.formulario_completo:
        return redirect(url_for("participante.bienvenida"))
    return render_template("participante/gracias.html", participante=participante)
