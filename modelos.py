"""Modelos de base de datos (capa de persistencia). Reflejan el diagrama entidad-relación."""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

bd = SQLAlchemy()

ROLES = ["Desarrollador", "Tester / QA", "Scrum Master", "Líder técnico"]
METODOLOGIAS = ["Scrum", "Kanban", "Híbrida"]
RANGOS_EXPERIENCIA = ["0–2 años", "3–5 años", "6–10 años", "Más de 10 años"]


def rango_experiencia(anios: int) -> str:
    if anios <= 2:
        return RANGOS_EXPERIENCIA[0]
    if anios <= 5:
        return RANGOS_EXPERIENCIA[1]
    if anios <= 10:
        return RANGOS_EXPERIENCIA[2]
    return RANGOS_EXPERIENCIA[3]


# ----------------------------- Organización -----------------------------
class Empresa(bd.Model):
    __tablename__ = "empresa"
    id_empresa = bd.Column(bd.Integer, primary_key=True)
    nombre = bd.Column(bd.String(80), nullable=False, unique=True)
    equipos = bd.relationship("EquipoDesarrollo", backref="empresa", cascade="all, delete-orphan")


class EquipoDesarrollo(bd.Model):
    __tablename__ = "equipo_desarrollo"
    id_equipo = bd.Column(bd.Integer, primary_key=True)
    id_empresa = bd.Column(bd.Integer, bd.ForeignKey("empresa.id_empresa"), nullable=False)
    nombre = bd.Column(bd.String(80), nullable=False)
    metodologia_trabajo = bd.Column(bd.String(20), nullable=False, default="Scrum")
    participantes = bd.relationship("Participante", backref="equipo")
    reportes = bd.relationship("ReporteMetricas", backref="equipo")

    __table_args__ = (bd.UniqueConstraint("id_empresa", "nombre", name="uq_equipo_empresa"),)


class Participante(bd.Model):
    __tablename__ = "participante"
    codigo_anonimo = bd.Column(bd.String(12), primary_key=True)
    id_equipo = bd.Column(bd.Integer, bd.ForeignKey("equipo_desarrollo.id_equipo"), nullable=False)
    rol_profesional = bd.Column(bd.String(30), nullable=False)
    anios_experiencia = bd.Column(bd.Integer, nullable=False)
    estado_formulario = bd.Column(bd.String(20), nullable=False, default="en_progreso")
    fecha_consentimiento = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    fecha_fin_bfi44 = bd.Column(bd.DateTime)
    fecha_fin_escala = bd.Column(bd.DateTime)

    respuestas_bfi = bd.relationship("RespuestaBFI44", backref="participante", cascade="all, delete-orphan")
    respuestas_escala = bd.relationship("RespuestaEscala", backref="participante", cascade="all, delete-orphan")
    puntaje = bd.relationship(
        "PuntajeParticipante", backref="participante", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def formulario_completo(self) -> bool:
        return self.estado_formulario == "completo"


# ------------------------------ Instrumentos ------------------------------
class RespuestaBFI44(bd.Model):
    __tablename__ = "respuesta_bfi44"
    id_respuesta = bd.Column(bd.Integer, primary_key=True)
    codigo_anonimo = bd.Column(bd.String(12), bd.ForeignKey("participante.codigo_anonimo"), nullable=False)
    numero_item = bd.Column(bd.Integer, nullable=False)
    valor_likert = bd.Column(bd.Integer, nullable=False)
    __table_args__ = (bd.UniqueConstraint("codigo_anonimo", "numero_item", name="uq_bfi_participante_item"),)


class RespuestaEscala(bd.Model):
    __tablename__ = "respuesta_escala"
    id_respuesta = bd.Column(bd.Integer, primary_key=True)
    codigo_anonimo = bd.Column(bd.String(12), bd.ForeignKey("participante.codigo_anonimo"), nullable=False)
    numero_item = bd.Column(bd.Integer, nullable=False)
    valor_likert = bd.Column(bd.Integer, nullable=False)
    __table_args__ = (bd.UniqueConstraint("codigo_anonimo", "numero_item", name="uq_escala_participante_item"),)


class PuntajeParticipante(bd.Model):
    """Puntajes derivados (RF-13)."""
    __tablename__ = "puntaje_participante"
    codigo_anonimo = bd.Column(bd.String(12), bd.ForeignKey("participante.codigo_anonimo"), primary_key=True)
    apertura = bd.Column(bd.Float, nullable=False)
    responsabilidad = bd.Column(bd.Float, nullable=False)
    extraversion = bd.Column(bd.Float, nullable=False)
    amabilidad = bd.Column(bd.Float, nullable=False)
    neuroticismo = bd.Column(bd.Float, nullable=False)
    rendimiento_autopercibido = bd.Column(bd.Float, nullable=False)


# ---------------------------- Integración de métricas ----------------------------
class Usuario(bd.Model):
    """Investigadora (usuario administrador)."""
    __tablename__ = "usuario_admin"
    id_usuario = bd.Column(bd.Integer, primary_key=True)
    usuario = bd.Column(bd.String(40), nullable=False, unique=True)
    hash_contrasena = bd.Column(bd.String(255), nullable=False)
    intentos_fallidos = bd.Column(bd.Integer, nullable=False, default=0)
    bloqueado_hasta = bd.Column(bd.DateTime)
    sesiones = bd.relationship("Sesion", backref="usuario", cascade="all, delete-orphan")
    reportes = bd.relationship("ReporteMetricas", backref="usuario")


class Sesion(bd.Model):
    __tablename__ = "sesion"
    id_sesion = bd.Column(bd.Integer, primary_key=True)
    id_usuario = bd.Column(bd.Integer, bd.ForeignKey("usuario_admin.id_usuario"), nullable=False)
    fecha_inicio = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    ultima_actividad = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    fecha_cierre = bd.Column(bd.DateTime)
    motivo_cierre = bd.Column(bd.String(20))  # manual | inactividad


class ReporteMetricas(bd.Model):
    __tablename__ = "reporte_metricas"
    id_reporte = bd.Column(bd.Integer, primary_key=True)
    id_equipo = bd.Column(bd.Integer, bd.ForeignKey("equipo_desarrollo.id_equipo"), nullable=False)
    id_usuario = bd.Column(bd.Integer, bd.ForeignKey("usuario_admin.id_usuario"), nullable=False)
    periodo_inicio = bd.Column(bd.Date, nullable=False)
    periodo_fin = bd.Column(bd.Date, nullable=False)
    nombre_archivo = bd.Column(bd.String(120), nullable=False)
    formato = bd.Column(bd.String(10), nullable=False)
    fecha_carga = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    registros_procesados = bd.Column(bd.Integer, nullable=False)
    metricas = bd.relationship("MetricaRendimiento", backref="reporte", cascade="all, delete-orphan")


class MetricaRendimiento(bd.Model):
    __tablename__ = "metrica_rendimiento"
    id_metrica = bd.Column(bd.Integer, primary_key=True)
    id_reporte = bd.Column(bd.Integer, bd.ForeignKey("reporte_metricas.id_reporte"), nullable=False)
    codigo_anonimo = bd.Column(bd.String(12), nullable=False, index=True)
    issues_completados = bd.Column(bd.Integer, nullable=False)
    story_points = bd.Column(bd.Float, nullable=False)
    bugs_resueltos = bd.Column(bd.Integer, nullable=False)
    tiempo_ciclo_dias = bd.Column(bd.Float, nullable=False)
    __table_args__ = (bd.UniqueConstraint("id_reporte", "codigo_anonimo", name="uq_metrica_reporte_codigo"),)


class Emparejamiento(bd.Model):
    __tablename__ = "emparejamiento"
    id_emparejamiento = bd.Column(bd.Integer, primary_key=True)
    fecha_ejecucion = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    n_emparejados = bd.Column(bd.Integer, nullable=False, default=0)
    n_sin_coincidencia = bd.Column(bd.Integer, nullable=False, default=0)
    codigos_excluidos = bd.Column(bd.Text, default="")  # separados por coma, solo códigos anónimos
    estado = bd.Column(bd.String(20), nullable=False, default="completo")
    registros = bd.relationship("RegistroEmparejado", backref="emparejamiento", cascade="all, delete-orphan")
    analisis = bd.relationship("Analisis", backref="emparejamiento", cascade="all, delete-orphan")


class RegistroEmparejado(bd.Model):
    __tablename__ = "registro_emparejado"
    id_emparejamiento = bd.Column(bd.Integer, bd.ForeignKey("emparejamiento.id_emparejamiento"), primary_key=True)
    codigo_anonimo = bd.Column(bd.String(12), bd.ForeignKey("participante.codigo_anonimo"), primary_key=True)
    id_metrica = bd.Column(bd.Integer, bd.ForeignKey("metrica_rendimiento.id_metrica"), nullable=False)
    participante = bd.relationship("Participante")
    metrica = bd.relationship("MetricaRendimiento")


# ------------------------------ Análisis ------------------------------
class Analisis(bd.Model):
    __tablename__ = "analisis"
    id_analisis = bd.Column(bd.Integer, primary_key=True)
    id_emparejamiento = bd.Column(bd.Integer, bd.ForeignKey("emparejamiento.id_emparejamiento"), nullable=False)
    fecha_ejecucion = bd.Column(bd.DateTime, nullable=False, default=datetime.now)
    n_muestra = bd.Column(bd.Integer, nullable=False)
    estado = bd.Column(bd.String(30), nullable=False)  # completo | datos_insuficientes
    advertencias = bd.Column(bd.Text, default="")  # una por línea
    correlaciones = bd.relationship("ResultadoCorrelacion", backref="analisis", cascade="all, delete-orphan")
    subgrupos = bd.relationship("ResultadoSubgrupo", backref="analisis", cascade="all, delete-orphan")
    descriptivos = bd.relationship("EstadisticoDescriptivo", backref="analisis", cascade="all, delete-orphan")


class ResultadoCorrelacion(bd.Model):
    __tablename__ = "resultado_correlacion"
    id_resultado = bd.Column(bd.Integer, primary_key=True)
    id_analisis = bd.Column(bd.Integer, bd.ForeignKey("analisis.id_analisis"), nullable=False)
    dimension = bd.Column(bd.String(20), nullable=False)
    variable_rendimiento = bd.Column(bd.String(30), nullable=False)
    prueba = bd.Column(bd.String(20), nullable=False)  # Spearman
    coeficiente = bd.Column(bd.Float, nullable=False)
    p_valor = bd.Column(bd.Float, nullable=False)
    n = bd.Column(bd.Integer, nullable=False)

    @property
    def significativo(self) -> bool:
        return self.p_valor < 0.05


class ResultadoSubgrupo(bd.Model):
    __tablename__ = "resultado_subgrupo"
    id_resultado = bd.Column(bd.Integer, primary_key=True)
    id_analisis = bd.Column(bd.Integer, bd.ForeignKey("analisis.id_analisis"), nullable=False)
    variable_agrupacion = bd.Column(bd.String(20), nullable=False)  # rol | experiencia
    variable_comparada = bd.Column(bd.String(30), nullable=False)
    prueba = bd.Column(bd.String(20), nullable=False)  # Kruskal-Wallis
    estadistico = bd.Column(bd.Float, nullable=False)
    p_valor = bd.Column(bd.Float, nullable=False)
    grupos_incluidos = bd.Column(bd.Integer, nullable=False)
    grupos_excluidos = bd.Column(bd.String(200), default="")

    @property
    def significativo(self) -> bool:
        return self.p_valor < 0.05


class EstadisticoDescriptivo(bd.Model):
    __tablename__ = "estadistico_descriptivo"
    id_estadistico = bd.Column(bd.Integer, primary_key=True)
    id_analisis = bd.Column(bd.Integer, bd.ForeignKey("analisis.id_analisis"), nullable=False)
    agrupacion = bd.Column(bd.String(20), nullable=False)  # global | rol | experiencia | metodologia
    categoria = bd.Column(bd.String(40), nullable=False)
    variable = bd.Column(bd.String(30), nullable=False)
    frecuencia = bd.Column(bd.Integer, nullable=False)
    media = bd.Column(bd.Float)
    desviacion = bd.Column(bd.Float)
