"""Punto de entrada de la plataforma de análisis Big Five – rendimiento laboral.

Ejecución:  python app.py
"""
import secrets

from flask import Flask, abort, render_template, request, session

from configuracion import Configuracion
from modelos import Empresa, EquipoDesarrollo, bd


def crear_aplicacion(configuracion=Configuracion) -> Flask:
    aplicacion = Flask(__name__, template_folder="plantillas", static_folder="estatico")
    aplicacion.config.from_object(configuracion)
    bd.init_app(aplicacion)

    from rutas.administracion import plano_administracion
    from rutas.participante import plano_participante

    aplicacion.register_blueprint(plano_participante)
    aplicacion.register_blueprint(plano_administracion)

    @aplicacion.before_request
    def proteger_con_token_csrf():
        if "token_csrf" not in session:
            session["token_csrf"] = secrets.token_urlsafe(32)
        if request.method == "POST":
            enviado = request.form.get("token_csrf") or request.headers.get("X-Token-CSRF")
            if not enviado or not secrets.compare_digest(enviado, session["token_csrf"]):
                abort(400, "Token de seguridad inválido. Recargue la página e intente nuevamente.")

    @aplicacion.context_processor
    def variables_globales():
        return {"token_csrf": session.get("token_csrf", "")}

    @aplicacion.after_request
    def cabeceras_seguridad(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/admin"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    @aplicacion.errorhandler(400)
    @aplicacion.errorhandler(404)
    @aplicacion.errorhandler(413)
    def pagina_de_error(error):
        mensajes = {400: getattr(error, "description", "Solicitud no válida."),
                    404: "La página que busca no existe.",
                    413: "El archivo supera el tamaño máximo permitido (5 MB)."}
        return render_template("error.html", codigo=error.code, mensaje=mensajes.get(error.code)), error.code

    with aplicacion.app_context():
        bd.create_all()
        sembrar_datos_iniciales()
    return aplicacion


def sembrar_datos_iniciales() -> None:
    """Crea las empresas del estudio y un equipo inicial por empresa (editable desde el panel)."""
    if Empresa.query.count() > 0:
        return
    for nombre in ("D&T Integra", "Paulonia"):
        empresa = Empresa(nombre=nombre)
        empresa.equipos.append(EquipoDesarrollo(nombre="Equipo de desarrollo 1", metodologia_trabajo="Scrum"))
        bd.session.add(empresa)
    bd.session.commit()


if __name__ == "__main__":
    crear_aplicacion().run(host="127.0.0.1", port=5000, debug=False)
