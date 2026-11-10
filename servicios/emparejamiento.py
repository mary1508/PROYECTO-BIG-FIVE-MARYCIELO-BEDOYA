"""Emparejamiento por código anónimo (CU4, RF-11, RF-12, RF-24)."""
from modelos import (
    Emparejamiento, MetricaRendimiento, Participante, RegistroEmparejado, ReporteMetricas, bd,
)


class PrecondicionFaltante(Exception):
    """Falta información de una etapa previa (RF-24). Lleva el mensaje y la acción sugerida."""

    def __init__(self, mensaje: str, accion: str, enlace: str):
        super().__init__(mensaje)
        self.mensaje, self.accion, self.enlace = mensaje, accion, enlace


def verificar_precondiciones() -> None:
    if Participante.query.filter_by(estado_formulario="completo").count() == 0:
        raise PrecondicionFaltante("Aún no hay participantes con el formulario completo.",
                                   "Comparta el enlace del formulario con los participantes.", "/")
    if ReporteMetricas.query.count() == 0:
        raise PrecondicionFaltante("Aún no se ha cargado ningún reporte de métricas.",
                                   "Cargue el reporte exportado de Jira o Azure DevOps.", "/admin/reportes")


def ejecutar_emparejamiento() -> Emparejamiento:
    """Cruza participantes completos con métricas por código anónimo, sin duplicados ni huérfanos."""
    verificar_precondiciones()

    completos = {p.codigo_anonimo: p for p in Participante.query.filter_by(estado_formulario="completo")}

    # Si un código aparece en varios reportes se usa la métrica del reporte más reciente.
    metricas_por_codigo: dict[str, MetricaRendimiento] = {}
    consulta = (MetricaRendimiento.query.join(ReporteMetricas)
                .order_by(ReporteMetricas.fecha_carga.asc(), MetricaRendimiento.id_metrica.asc()))
    for metrica in consulta:
        metricas_por_codigo[metrica.codigo_anonimo] = metrica

    codigos_emparejados = sorted(set(completos) & set(metricas_por_codigo))
    solo_formulario = set(completos) - set(metricas_por_codigo)
    solo_metricas = set(metricas_por_codigo) - set(completos)
    excluidos = sorted(solo_formulario | solo_metricas)

    emparejamiento = Emparejamiento(
        n_emparejados=len(codigos_emparejados), n_sin_coincidencia=len(excluidos),
        codigos_excluidos=",".join(excluidos), estado="completo",
    )
    for codigo in codigos_emparejados:
        emparejamiento.registros.append(RegistroEmparejado(
            codigo_anonimo=codigo, id_metrica=metricas_por_codigo[codigo].id_metrica))
    bd.session.add(emparejamiento)
    bd.session.commit()
    return emparejamiento


def ultimo_emparejamiento() -> Emparejamiento | None:
    return Emparejamiento.query.order_by(Emparejamiento.id_emparejamiento.desc()).first()
