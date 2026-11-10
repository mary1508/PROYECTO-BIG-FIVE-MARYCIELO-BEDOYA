"""Pruebas de integración del flujo completo: formulario → ingreso → carga → emparejamiento → análisis → dashboard."""
import io
import random

from modelos import Participante, ReporteMetricas
from servicios import formulario
from servicios.analisis import ejecutar_analisis
from servicios.emparejamiento import PrecondicionFaltante, ejecutar_emparejamiento
from pruebas.conftest import extraer_token, iniciar_sesion
import pytest
from modelos import EquipoDesarrollo, bd


def crear_participantes(aplicacion, cantidad=24):
    azar = random.Random(1)
    codigos = []
    with aplicacion.app_context():
        equipo = EquipoDesarrollo.query.first()
        roles = ["Desarrollador", "Tester / QA", "Scrum Master", "Líder técnico"]
        for i in range(cantidad):
            p = formulario.registrar_participante(equipo, roles[i % 2 if i < 20 else 2 + i % 2], i % 12)
            formulario.guardar_bfi44(p, {n: azar.randint(1, 5) for n in range(1, 45)})
            formulario.guardar_escala_y_finalizar(p, {n: azar.randint(1, 5) for n in range(1, 9)})
            codigos.append(p.codigo_anonimo)
    return codigos


def csv_metricas(codigos, extra=""):
    azar = random.Random(2)
    filas = ["codigo_anonimo,issues_completados,story_points,bugs_resueltos,tiempo_ciclo_dias"]
    for c in codigos:
        filas.append(f"{c},{azar.randint(5, 25)},{azar.randint(10, 50)},{azar.randint(0, 9)},{azar.uniform(1, 6):.1f}")
    return ("\n".join(filas) + "\n" + extra).encode()


def subir(cliente, contenido, nombre="reporte.csv", inicio="2026-03-01", fin="2026-05-15"):
    token = extraer_token(cliente, "/admin/reportes")
    return cliente.post("/admin/reportes", data={
        "token_csrf": token, "id_equipo": "1", "periodo_inicio": inicio, "periodo_fin": fin,
        "archivo": (io.BytesIO(contenido), nombre)}, content_type="multipart/form-data")


# ---------------------------------------------------------------- Participante
def test_formulario_publico_completo(cliente, aplicacion):
    token = extraer_token(cliente)
    assert cliente.post("/iniciar", data={"token_csrf": token}).status_code == 400  # sin consentimiento
    cliente.post("/iniciar", data={"token_csrf": token, "consentimiento": "si"})
    r = cliente.post("/perfil", data={"token_csrf": token, "id_equipo": "1", "rol": "Desarrollador", "anios_experiencia": "4"})
    assert r.status_code == 302
    # Envío incompleto: se rechaza y señala faltantes (RF-06)
    r = cliente.post("/cuestionario", data={"token_csrf": token, "item_1": "3"})
    assert r.status_code == 400 and "Faltan 43" in r.get_data(as_text=True)
    cliente.post("/cuestionario", data={"token_csrf": token, **{f"item_{n}": "4" for n in range(1, 45)}})
    cliente.post("/escala-rendimiento", data={"token_csrf": token, **{f"item_{n}": "5" for n in range(1, 9)}})
    with aplicacion.app_context():
        p = Participante.query.one()
        assert p.estado_formulario == "completo" and p.codigo_anonimo.startswith("BF-")
        assert len(p.respuestas_bfi) == 44 and p.puntaje.rendimiento_autopercibido == 5
    assert "Gracias" in cliente.get("/gracias").get_data(as_text=True)


def test_no_se_puede_saltar_al_cuestionario_sin_perfil(cliente):
    assert cliente.get("/cuestionario").status_code == 302


def test_post_sin_token_csrf_es_rechazado(cliente):
    assert cliente.post("/iniciar", data={"consentimiento": "si"}).status_code == 400


# ---------------------------------------------------------------- Acceso (CU8)
def test_panel_exige_sesion(cliente):
    r = cliente.get("/admin/dashboard")
    assert r.status_code == 302 and "/admin/ingreso" in r.headers["Location"]


def test_credenciales_invalidas_mensaje_generico_y_bloqueo(cliente):
    mensajes = set()
    for _ in range(4):
        r = iniciar_sesion(cliente, "investigadora", "mala")
        assert r.status_code == 401
        mensajes.add("Usuario o contraseña incorrectos." in r.get_data(as_text=True))
    assert mensajes == {True}
    assert iniciar_sesion(cliente, "otro", "mala").status_code == 401  # usuario inexistente: mismo mensaje
    r = iniciar_sesion(cliente, "investigadora", "mala")  # 5.º intento fallido → bloqueo
    assert "bloqueado" in r.get_data(as_text=True)
    r = iniciar_sesion(cliente)  # aun con la clave correcta
    assert r.status_code == 401 and "bloqueado" in r.get_data(as_text=True)


def test_ingreso_correcto_y_cierre_manual(cliente):
    assert iniciar_sesion(cliente).status_code == 302
    assert cliente.get("/admin/").status_code == 200
    token = extraer_token(cliente, "/admin/")
    cliente.post("/admin/salir", data={"token_csrf": token})
    assert cliente.get("/admin/").status_code == 302


def test_sesion_expira_por_inactividad(cliente, aplicacion):
    from datetime import datetime, timedelta
    from modelos import Sesion
    iniciar_sesion(cliente)
    with aplicacion.app_context():
        s = Sesion.query.one()
        s.ultima_actividad = datetime.now() - timedelta(minutes=31)
        bd.session.commit()
    assert cliente.get("/admin/").status_code == 302


# ---------------------------------------------------------------- Carga de reportes (CU3)
def test_carga_valida_y_errores(cliente, aplicacion):
    codigos = crear_participantes(aplicacion)
    iniciar_sesion(cliente)
    assert subir(cliente, b"a,b\n1,2\n").status_code == 400                                  # faltan columnas
    r = subir(cliente, b"x", "datos.pdf")
    assert r.status_code == 400 and "Formato no soportado" in r.get_data(as_text=True)
    r = subir(cliente, csv_metricas(codigos, f"{codigos[0]},1,1,1,1\n"))                       # duplicado
    assert "duplicados" in r.get_data(as_text=True)
    r = subir(cliente, csv_metricas(codigos), inicio="2026-03-01", fin="2026-03-05")           # periodo corto
    assert r.status_code == 400
    r = subir(cliente, csv_metricas(codigos))
    assert r.status_code == 302
    with aplicacion.app_context():
        assert ReporteMetricas.query.one().registros_procesados == len(codigos)


# ---------------------------------------------------------------- Emparejamiento y análisis
def test_precondiciones(aplicacion):
    with aplicacion.app_context():
        with pytest.raises(PrecondicionFaltante):
            ejecutar_emparejamiento()
        with pytest.raises(PrecondicionFaltante):
            ejecutar_analisis()


def test_emparejamiento_excluye_huerfanos_y_analiza(cliente, aplicacion):
    codigos = crear_participantes(aplicacion)
    iniciar_sesion(cliente)
    # Se quita un participante del reporte y se agrega un código inexistente.
    subir(cliente, csv_metricas(codigos[1:], "BF-ZZZZZZ,3,3,3,3\n"))
    with aplicacion.app_context():
        emp = ejecutar_emparejamiento()
        assert emp.n_emparejados == len(codigos) - 1
        assert emp.n_sin_coincidencia == 2
        assert set(emp.codigos_excluidos.split(",")) == {codigos[0], "BF-ZZZZZZ"}
        # Sin duplicados
        claves = [r.codigo_anonimo for r in emp.registros]
        assert len(claves) == len(set(claves))
        analisis = ejecutar_analisis()
        assert analisis.estado == "completo" and analisis.n_muestra == len(codigos) - 1
        assert len(analisis.correlaciones) == 25          # 5 dimensiones × 5 indicadores
        assert all(r.prueba == "Spearman" and -1 <= r.coeficiente <= 1 for r in analisis.correlaciones)
        assert all(s.prueba == "Kruskal-Wallis" for s in analisis.subgrupos) and analisis.subgrupos


def test_muestra_insuficiente_solo_descriptiva(cliente, aplicacion):
    codigos = crear_participantes(aplicacion, cantidad=6)
    iniciar_sesion(cliente)
    subir(cliente, csv_metricas(codigos))
    with aplicacion.app_context():
        ejecutar_emparejamiento()
        analisis = ejecutar_analisis()
        assert analisis.estado == "datos_insuficientes"
        assert not analisis.correlaciones and analisis.descriptivos


def test_dashboard_y_api_con_filtros(cliente, aplicacion):
    codigos = crear_participantes(aplicacion)
    iniciar_sesion(cliente)
    subir(cliente, csv_metricas(codigos))
    token = extraer_token(cliente, "/admin/emparejamiento")
    assert cliente.post("/admin/emparejamiento", data={"token_csrf": token}).status_code == 302
    assert cliente.post("/admin/analisis", data={"token_csrf": token}).status_code == 302
    pagina = cliente.get("/admin/dashboard")
    assert pagina.status_code == 200 and "Dashboard de resultados" in pagina.get_data(as_text=True)
    datos = cliente.get("/admin/api/dashboard").get_json()
    assert len(datos["correlaciones"]) == 5 and datos["analisis"]["n"] == len(codigos)
    una = cliente.get("/admin/api/dashboard?dimension=apertura&variable=story_points&rol=Desarrollador").get_json()
    assert len(una["correlaciones"]) == 1 and una["dispersion"] and all(p["rol"] == "Desarrollador" for p in una["dispersion"])
