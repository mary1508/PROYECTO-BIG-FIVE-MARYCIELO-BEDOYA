"""Verificaciones no funcionales del plan de pruebas: RNF-05, RNF-12, RNF-17, RNF-18 y RNF-20."""
import re
import time

from sqlalchemy import inspect

from modelos import Usuario, bd
from pruebas.conftest import iniciar_sesion
from pruebas.test_flujo_completo import crear_participantes, csv_metricas, subir
from servicios.analisis import ejecutar_analisis
from servicios.emparejamiento import ejecutar_emparejamiento


def test_rnf05_esquema_sin_datos_de_identificacion(aplicacion):
    prohibidas = re.compile(r"nombre|apellido|correo|email|dni|telefono|celular|direccion", re.I)
    with aplicacion.app_context():
        inspector = inspect(bd.engine)
        columnas = {t: [c["name"] for c in inspector.get_columns(t)] for t in inspector.get_table_names()}
    encontradas = {t: [c for c in cols if prohibidas.search(c)] for t, cols in columnas.items()}
    # Solo se permiten nombres de empresa, de equipo y de archivo, nunca de personas.
    permitidas = {"empresa": ["nombre"], "equipo_desarrollo": ["nombre"], "reporte_metricas": ["nombre_archivo"]}
    assert {t: c for t, c in encontradas.items() if c and c != permitidas.get(t)} == {}
    assert "codigo_anonimo" in columnas["participante"]


def test_rnf20_contrasena_solo_como_hash_bcrypt(aplicacion):
    with aplicacion.app_context():
        usuario = Usuario.query.one()
        assert usuario.hash_contrasena.startswith("$2b$") and "clave-segura-1" not in usuario.hash_contrasena


def test_rnf12_rnf17_tiempos_con_200_registros(cliente, aplicacion, capsys):
    codigos = crear_participantes(aplicacion, cantidad=200)
    iniciar_sesion(cliente)
    t0 = time.perf_counter()
    assert subir(cliente, csv_metricas(codigos)).status_code == 302
    t_carga = time.perf_counter() - t0
    with aplicacion.app_context():
        t0 = time.perf_counter()
        emp = ejecutar_emparejamiento()
        t_emp = time.perf_counter() - t0
        assert emp.n_emparejados == 200
        t0 = time.perf_counter()
        analisis = ejecutar_analisis()
        t_analisis = time.perf_counter() - t0
        assert analisis.estado == "completo" and len(analisis.correlaciones) == 25
    t0 = time.perf_counter()
    assert cliente.get("/admin/api/dashboard?dimension=apertura&variable=story_points").status_code == 200
    t_filtro = time.perf_counter() - t0
    with capsys.disabled():
        print(f"\nRNF-12/17 (200 registros): carga {t_carga:.2f} s, emparejamiento {t_emp:.2f} s, "
              f"análisis {t_analisis:.2f} s, filtro {t_filtro:.2f} s")
    assert t_carga + t_emp <= 30 and t_analisis <= 60 and t_filtro <= 3


def test_rnf18_dos_ejecuciones_dan_resultados_identicos(cliente, aplicacion):
    codigos = crear_participantes(aplicacion, cantidad=40)
    iniciar_sesion(cliente)
    subir(cliente, csv_metricas(codigos))
    with aplicacion.app_context():
        ejecutar_emparejamiento()
        a, b = ejecutar_analisis(), ejecutar_analisis()
        ra = [(c.dimension, c.variable_rendimiento, c.coeficiente, c.p_valor) for c in a.correlaciones]
        rb = [(c.dimension, c.variable_rendimiento, c.coeficiente, c.p_valor) for c in b.correlaciones]
        sa = [(s.variable_comparada, s.estadistico, s.p_valor) for s in a.subgrupos]
        sb = [(s.variable_comparada, s.estadistico, s.p_valor) for s in b.subgrupos]
        assert ra == rb and sa == sb and len(ra) == 25
