"""Servicio del formulario del participante (CU1, CU2): código anónimo, validación y registro."""
import secrets
from datetime import datetime

from modelos import (
    EquipoDesarrollo, Participante, PuntajeParticipante, RespuestaBFI44, RespuestaEscala, ROLES, bd,
)
from servicios.instrumentos import (
    ITEMS_BFI44, ITEMS_ESCALA_RENDIMIENTO, TOTAL_ITEMS_BFI, TOTAL_ITEMS_ESCALA,
    calcular_puntajes_bfi, calcular_rendimiento_autopercibido,
)

ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin caracteres ambiguos (0/O, 1/I)


def generar_codigo_anonimo() -> str:
    """Código único e irrepetible, sin relación con datos personales (RF-01)."""
    while True:
        codigo = "BF-" + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))
        if not bd.session.get(Participante, codigo):
            return codigo


def validar_perfil(id_equipo, rol, anios) -> tuple[dict, list[str]]:
    errores = []
    equipo = None
    try:
        equipo = bd.session.get(EquipoDesarrollo, int(id_equipo))
    except (TypeError, ValueError):
        pass
    if equipo is None:
        errores.append("Seleccione su empresa y equipo.")
    if rol not in ROLES:
        errores.append("Seleccione su rol profesional.")
    try:
        anios_int = int(anios)
        if not 0 <= anios_int <= 50:
            raise ValueError
    except (TypeError, ValueError):
        anios_int = None
        errores.append("Ingrese sus años de experiencia (un número entre 0 y 50).")
    return {"equipo": equipo, "rol": rol, "anios": anios_int}, errores


def registrar_participante(equipo: EquipoDesarrollo, rol: str, anios: int) -> Participante:
    participante = Participante(
        codigo_anonimo=generar_codigo_anonimo(),
        id_equipo=equipo.id_equipo,
        rol_profesional=rol,
        anios_experiencia=anios,
        estado_formulario="en_progreso",
        fecha_consentimiento=datetime.now(),
    )
    bd.session.add(participante)
    bd.session.commit()
    return participante


def leer_respuestas(formulario, prefijo: str, total: int) -> tuple[dict[int, int], list[int]]:
    """Extrae respuestas del formulario HTML. Devuelve (respuestas válidas, ítems faltantes) (RF-06)."""
    respuestas, faltantes = {}, []
    for numero in range(1, total + 1):
        crudo = formulario.get(f"{prefijo}_{numero}")
        if crudo in {"1", "2", "3", "4", "5"}:
            respuestas[numero] = int(crudo)
        else:
            faltantes.append(numero)
    return respuestas, faltantes


def guardar_bfi44(participante: Participante, respuestas: dict[int, int]) -> None:
    if len(respuestas) != TOTAL_ITEMS_BFI:
        raise ValueError("Respuestas incompletas del BFI-44.")
    RespuestaBFI44.query.filter_by(codigo_anonimo=participante.codigo_anonimo).delete()
    for numero, valor in respuestas.items():
        bd.session.add(RespuestaBFI44(codigo_anonimo=participante.codigo_anonimo, numero_item=numero, valor_likert=valor))
    participante.fecha_fin_bfi44 = datetime.now()
    participante.estado_formulario = "bfi_completo"
    bd.session.commit()


def guardar_escala_y_finalizar(participante: Participante, respuestas: dict[int, int]) -> None:
    if len(respuestas) != TOTAL_ITEMS_ESCALA:
        raise ValueError("Respuestas incompletas de la escala.")
    RespuestaEscala.query.filter_by(codigo_anonimo=participante.codigo_anonimo).delete()
    for numero, valor in respuestas.items():
        bd.session.add(RespuestaEscala(codigo_anonimo=participante.codigo_anonimo, numero_item=numero, valor_likert=valor))
    participante.fecha_fin_escala = datetime.now()

    # Cálculo de puntajes (RF-13) a partir de lo guardado.
    respuestas_bfi = {r.numero_item: r.valor_likert for r in participante.respuestas_bfi}
    puntajes = calcular_puntajes_bfi(respuestas_bfi)
    rendimiento = calcular_rendimiento_autopercibido(respuestas)
    if participante.puntaje is None:
        participante.puntaje = PuntajeParticipante(codigo_anonimo=participante.codigo_anonimo, **puntajes,
                                                   rendimiento_autopercibido=rendimiento)
    else:
        for dimension, valor in puntajes.items():
            setattr(participante.puntaje, dimension, valor)
        participante.puntaje.rendimiento_autopercibido = rendimiento
    participante.estado_formulario = "completo"  # RF-07
    bd.session.commit()
