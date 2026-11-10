"""Rutas del panel de la investigadora (CU3 a CU8). Todas, salvo el ingreso, exigen sesión activa."""
from functools import wraps

from flask import (
    Blueprint, Response, flash, jsonify, redirect, render_template, request, session, url_for, current_app,
)

from modelos import (
    Analisis, Empresa, EquipoDesarrollo, MetricaRendimiento, METODOLOGIAS, Participante, ReporteMetricas, ROLES,
    RANGOS_EXPERIENCIA, Usuario, bd,
)
from servicios import analisis as servicio_analisis
from servicios import autenticacion
from servicios import emparejamiento as servicio_emparejamiento
from servicios import reportes as servicio_reportes
from servicios.emparejamiento import PrecondicionFaltante
from servicios.instrumentos import DIMENSIONES as ETIQUETAS_DIMENSION

plano_administracion = Blueprint("administracion", __name__, url_prefix="/admin")

ETIQUETAS_VARIABLE = {
    **ETIQUETAS_DIMENSION,
    "rendimiento_autopercibido": "Rendimiento autopercibido",
    "story_points": "Story points",
    "issues_completados": "Issues completados",
    "bugs_resueltos": "Bugs resueltos",
    "tiempo_ciclo_dias": "Tiempo de ciclo (días)",
}


def sesion_requerida(vista):
    """Restringe el acceso a módulos administrativos (RF-26)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        sesion = autenticacion.sesion_vigente(session.get("id_sesion"))
        if sesion is None:
            motivo = "expirada" if session.get("id_sesion") else "requerida"
            session.pop("id_sesion", None)
            flash("Su sesión expiró por inactividad. Inicie sesión nuevamente." if motivo == "expirada"
                  else "Inicie sesión para acceder al panel.", "aviso")
            return redirect(url_for("administracion.ingreso", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


@plano_administracion.app_context_processor
def contexto_administracion():
    return {"etiquetas": ETIQUETAS_VARIABLE, "hay_sesion": bool(session.get("id_sesion")),
            "nombre_usuario": session.get("nombre_usuario")}


# ------------------------------------------------------------------ Acceso (CU8)
@plano_administracion.route("/ingreso", methods=["GET", "POST"])
def ingreso():
    if autenticacion.sesion_vigente(session.get("id_sesion")):
        return redirect(url_for("administracion.inicio"))
    error = None
    if request.method == "POST":
        sesion, error = autenticacion.intentar_ingreso(request.form.get("usuario"), request.form.get("contrasena"))
        if sesion:
            session.clear()
            session["id_sesion"] = sesion.id_sesion
            session["nombre_usuario"] = sesion.usuario.usuario
            session.permanent = True
            destino = request.args.get("siguiente", "")
            return redirect(destino if destino.startswith("/admin") else url_for("administracion.inicio"))
    return render_template("admin/ingreso.html", error=error), (401 if error else 200)


@plano_administracion.route("/salir", methods=["POST"])
def salir():
    autenticacion.cerrar_sesion(session.get("id_sesion"))
    session.clear()
    flash("Sesión cerrada correctamente.", "exito")
    return redirect(url_for("administracion.ingreso"))


# ------------------------------------------------------------------ Panel de inicio
@plano_administracion.route("/")
@sesion_requerida
def inicio():
    emparejamiento = servicio_emparejamiento.ultimo_emparejamiento()
    analisis = servicio_analisis.ultimo_analisis()
    resumen = {
        "participantes_completos": Participante.query.filter_by(estado_formulario="completo").count(),
        "participantes_en_progreso": Participante.query.filter(Participante.estado_formulario != "completo").count(),
        "reportes": ReporteMetricas.query.count(),
        "emparejamiento": emparejamiento,
        "analisis": analisis,
    }
    return render_template("admin/inicio.html", resumen=resumen,
                           minimo=current_app.config["MUESTRA_MINIMA_EMPAREJADOS"])


# ------------------------------------------------------------------ Equipos
@plano_administracion.route("/equipos", methods=["GET", "POST"])
@sesion_requerida
def equipos():
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        metodologia = request.form.get("metodologia")
        empresa = bd.session.get(Empresa, int(request.form["id_empresa"])) if request.form.get("id_empresa", "").isdigit() else None
        if not nombre or empresa is None or metodologia not in METODOLOGIAS:
            flash("Complete empresa, nombre del equipo y metodología.", "error")
        elif EquipoDesarrollo.query.filter_by(id_empresa=empresa.id_empresa, nombre=nombre).first():
            flash("Ese equipo ya existe en la empresa seleccionada.", "error")
        else:
            bd.session.add(EquipoDesarrollo(id_empresa=empresa.id_empresa, nombre=nombre, metodologia_trabajo=metodologia))
            bd.session.commit()
            flash(f"Equipo «{nombre}» registrado.", "exito")
        return redirect(url_for("administracion.equipos"))
    return render_template("admin/equipos.html", empresas=Empresa.query.order_by(Empresa.nombre).all(),
                           metodologias=METODOLOGIAS)


# ------------------------------------------------------------------ Carga de reportes (CU3)
@plano_administracion.route("/reportes", methods=["GET", "POST"])
@sesion_requerida
def reportes():
    errores, resultado = [], None
    if request.method == "POST":
        archivo = request.files.get("archivo")
        resultado = servicio_reportes.procesar_reporte(
            request.form.get("id_equipo"), request.form.get("periodo_inicio"), request.form.get("periodo_fin"),
            archivo.filename if archivo else "", archivo.read() if archivo else b"",
            Usuario.query.filter_by(usuario=session.get("nombre_usuario")).first().id_usuario,
            current_app.config["EXTENSIONES_PERMITIDAS"])
        if resultado.exito:
            flash(f"Reporte cargado: {resultado.registros_procesados} registros procesados.", "exito")
            return redirect(url_for("administracion.reportes"))
        errores = resultado.errores
    return render_template(
        "admin/reportes.html", empresas=Empresa.query.order_by(Empresa.nombre).all(), errores=errores,
        historial=ReporteMetricas.query.order_by(ReporteMetricas.fecha_carga.desc()).limit(20).all(),
        columnas=servicio_reportes.COLUMNAS_ESPERADAS, datos=request.form), (400 if errores else 200)


@plano_administracion.route("/reportes/plantilla")
@sesion_requerida
def plantilla_reporte():
    return Response(servicio_reportes.TEXTO_PLANTILLA, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=plantilla_reporte_metricas.csv"})


# ------------------------------------------------------------------ Emparejamiento (CU4)
@plano_administracion.route("/emparejamiento", methods=["GET", "POST"])
@sesion_requerida
def emparejamiento():
    precondicion = None
    if request.method == "POST":
        try:
            nuevo = servicio_emparejamiento.ejecutar_emparejamiento()
            flash(f"Emparejamiento ejecutado: {nuevo.n_emparejados} emparejados, {nuevo.n_sin_coincidencia} sin coincidencia.",
                  "exito")
            return redirect(url_for("administracion.emparejamiento"))
        except PrecondicionFaltante as error:
            precondicion = error
    ultimo = servicio_emparejamiento.ultimo_emparejamiento()
    excluidos = [c for c in (ultimo.codigos_excluidos or "").split(",") if c] if ultimo else []
    completos = {p.codigo_anonimo for p in Participante.query.filter_by(estado_formulario="completo")}
    return render_template("admin/emparejamiento.html", ultimo=ultimo, precondicion=precondicion,
                           excluidos=[{"codigo": c, "motivo": "Sin métricas" if c in completos else "Sin formulario completo"}
                                      for c in excluidos]), (409 if precondicion else 200)


# ------------------------------------------------------------------ Análisis (CU5)
@plano_administracion.route("/analisis", methods=["GET", "POST"])
@sesion_requerida
def analisis():
    precondicion = None
    if request.method == "POST":
        try:
            nuevo = servicio_analisis.ejecutar_analisis()
            flash("Análisis ejecutado y guardado." if nuevo.estado == "completo"
                  else "Análisis ejecutado con datos insuficientes: solo se calculó la estadística descriptiva.",
                  "exito" if nuevo.estado == "completo" else "aviso")
            return redirect(url_for("administracion.analisis"))
        except PrecondicionFaltante as error:
            precondicion = error
    ultimo = servicio_analisis.ultimo_analisis()
    return render_template("admin/analisis.html", ultimo=ultimo, precondicion=precondicion,
                           advertencias=[a for a in (ultimo.advertencias or "").split("\n") if a] if ultimo else [],
                           minimo=current_app.config["MUESTRA_MINIMA_EMPAREJADOS"]), (409 if precondicion else 200)


# ------------------------------------------------------------------ Dashboard (CU6, CU7)
@plano_administracion.route("/dashboard")
@sesion_requerida
def dashboard():
    ultimo = servicio_analisis.ultimo_analisis()
    if ultimo is None:
        return render_template("admin/dashboard.html", ultimo=None,
                               precondicion=PrecondicionFaltante(
                                   "Aún no se ha ejecutado el análisis estadístico.",
                                   "Ejecute el análisis para poder visualizar los resultados.", "/admin/analisis"))
    return render_template("admin/dashboard.html", ultimo=ultimo, precondicion=None, roles=ROLES,
                           experiencias=RANGOS_EXPERIENCIA, metodologias=METODOLOGIAS,
                           dimensiones=ETIQUETAS_DIMENSION, variables=ETIQUETAS_VARIABLE)


@plano_administracion.route("/api/dashboard")
@sesion_requerida
def api_dashboard():
    """Resultados ya almacenados, filtrados (RF-19, RF-21). No se recalcula ninguna prueba."""
    ultimo = servicio_analisis.ultimo_analisis()
    if ultimo is None:
        return jsonify({"error": "Sin análisis."}), 409
    dimension = request.args.get("dimension", "todas")
    variable = request.args.get("variable", "rendimiento_autopercibido")
    rol, experiencia, metodologia = (request.args.get(c, "todos") for c in ("rol", "experiencia", "metodologia"))
    if variable not in servicio_analisis.VARIABLES_RENDIMIENTO:
        variable = "rendimiento_autopercibido"
    dimensiones = list(ETIQUETAS_DIMENSION) if dimension == "todas" else [dimension]

    correlaciones = [{
        "dimension": r.dimension, "etiqueta": ETIQUETAS_VARIABLE[r.dimension], "prueba": r.prueba,
        "coeficiente": round(r.coeficiente, 4), "p_valor": r.p_valor, "significativo": r.significativo, "n": r.n,
    } for r in ultimo.correlaciones if r.dimension in dimensiones and r.variable_rendimiento == variable]

    subgrupos = [{
        "agrupacion": s.variable_agrupacion, "variable": ETIQUETAS_VARIABLE[s.variable_comparada], "prueba": s.prueba,
        "estadistico": round(s.estadistico, 4), "p_valor": s.p_valor, "significativo": s.significativo,
        "grupos": s.grupos_incluidos, "excluidos": s.grupos_excluidos,
    } for s in ultimo.subgrupos if s.variable_comparada in dimensiones + ["rendimiento_autopercibido"]
        and (s.variable_comparada in dimensiones)]

    seleccion = {"rol": rol, "experiencia": experiencia, "metodologia": metodologia}
    frecuencias = {"rol": [], "experiencia": [], "metodologia": []}
    medias_grupo = {"rol": [], "experiencia": [], "metodologia": []}
    descriptivo_global = []
    for d in ultimo.descriptivos:
        if d.agrupacion == "global" and d.variable in ETIQUETAS_VARIABLE:
            descriptivo_global.append({"variable": ETIQUETAS_VARIABLE[d.variable], "clave": d.variable,
                                       "media": round(d.media, 3), "desviacion": round(d.desviacion or 0, 3),
                                       "n": d.frecuencia})
        elif d.agrupacion in frecuencias and seleccion[d.agrupacion] in ("todos", d.categoria):
            if d.variable == "apertura":  # una fila por categoría para las frecuencias
                frecuencias[d.agrupacion].append({"categoria": d.categoria, "n": d.frecuencia})
            for dim in dimensiones:
                if d.variable == dim:
                    medias_grupo[d.agrupacion].append({"categoria": d.categoria, "variable": ETIQUETAS_VARIABLE[dim],
                                                       "media": round(d.media, 3), "desviacion": round(d.desviacion or 0, 3),
                                                       "n": d.frecuencia})

    tabla = servicio_analisis.construir_tabla_emparejada(ultimo.emparejamiento)
    for columna, valor in (("rol", rol), ("experiencia", experiencia), ("metodologia", metodologia)):
        if valor != "todos":
            tabla = tabla[tabla[columna] == valor]
    dispersion = [{"x": round(float(f[dimensiones[0]]), 3), "y": round(float(f[variable]), 3), "rol": f["rol"]}
                  for _, f in tabla.iterrows()] if len(dimensiones) == 1 else []

    return jsonify({
        "analisis": {"fecha": ultimo.fecha_ejecucion.strftime("%d/%m/%Y %H:%M"), "n": ultimo.n_muestra,
                     "estado": ultimo.estado, "advertencias": [a for a in (ultimo.advertencias or "").split("\n") if a]},
        "variable_nombre": ETIQUETAS_VARIABLE[variable],
        "correlaciones": correlaciones, "subgrupos": subgrupos, "frecuencias": frecuencias,
        "medias_grupo": medias_grupo, "descriptivo_global": descriptivo_global,
        "dispersion": dispersion, "etiqueta_x": ETIQUETAS_VARIABLE.get(dimensiones[0]) if len(dimensiones) == 1 else None,
    })
