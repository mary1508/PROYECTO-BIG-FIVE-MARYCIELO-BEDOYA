"""Casos de prueba CP-04, CP-10, CP-15 y CP-16 del plan de pruebas (Capítulo IV de la tesis)."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from app import crear_aplicacion
from configuracion import Configuracion
from modelos import EquipoDesarrollo
from pruebas.conftest import extraer_token, iniciar_sesion
from pruebas.test_flujo_completo import crear_participantes, csv_metricas, subir
from servicios.analisis import DIMENSIONES, ejecutar_analisis, comparar_grupos, construir_tabla_emparejada
from servicios.autenticacion import crear_usuario
from servicios.emparejamiento import ejecutar_emparejamiento
from servicios.reportes import validar_periodo


# ------------------------------------------------------------------ CP-04
def test_cp04_escala_incompleta_es_rechazada(cliente):
    token = extraer_token(cliente)
    cliente.post("/iniciar", data={"token_csrf": token, "consentimiento": "si"})
    cliente.post("/perfil", data={"token_csrf": token, "id_equipo": "1", "rol": "Desarrollador",
                                  "anios_experiencia": "4"})
    cliente.post("/cuestionario", data={"token_csrf": token, **{f"item_{n}": "4" for n in range(1, 45)}})
    r = cliente.post("/escala-rendimiento", data={"token_csrf": token, **{f"item_{n}": "5" for n in range(1, 8)}})
    assert r.status_code == 400 and "Faltan 1" in r.get_data(as_text=True)


# ------------------------------------------------------------------ CP-10
@pytest.mark.parametrize("dias,aceptado", [(5, False), (13, False), (14, True), (120, True), (121, False)])
def test_cp10_limites_del_periodo(dias, aceptado):
    inicio = date(2026, 3, 1)
    fin = inicio + timedelta(days=dias - 1)
    _, _, error = validar_periodo(inicio.isoformat(), fin.isoformat())
    assert (error is None) == aceptado


# ------------------------------------------------------------------ CP-15
@pytest.fixture
def aplicacion_real(tmp_path):
    """Usa los mínimos reales de la tesis (30 pares y 5 por subgrupo), sin reducirlos."""
    class ConfiguracionReal(Configuracion):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(tmp_path / "real.db")
    app = crear_aplicacion(ConfiguracionReal)
    with app.app_context():
        crear_usuario("investigadora", "clave-segura-1")
    return app


@pytest.mark.parametrize("cantidad,estado", [(29, "datos_insuficientes"), (30, "completo")])
def test_cp15_limite_de_muestra_con_configuracion_real(aplicacion_real, cantidad, estado):
    assert aplicacion_real.config["MUESTRA_MINIMA_EMPAREJADOS"] == 30
    cliente = aplicacion_real.test_client()
    codigos = crear_participantes(aplicacion_real, cantidad=cantidad)
    iniciar_sesion(cliente)
    subir(cliente, csv_metricas(codigos))
    with aplicacion_real.app_context():
        ejecutar_emparejamiento()
        assert ejecutar_analisis().estado == estado


def test_cp15_limite_de_subgrupo_4_y_5():
    tabla = pd.DataFrame({"rol": ["A"] * 5 + ["B"] * 5 + ["C"] * 4,
                          "apertura": [1, 2, 3, 4, 5, 2, 3, 4, 5, 1, 3, 3, 4, 4]})
    prueba, h, p, n_grupos, excluidos = comparar_grupos(tabla, "rol", "apertura", 5)
    assert prueba == "Kruskal-Wallis" and n_grupos == 2 and excluidos == ["C (n=4)"]


# ------------------------------------------------------------------ CP-16
def _rangos(valores):
    """Rangos con promedio en empates, calculados a mano (sin scipy.stats.rankdata)."""
    v = np.asarray(valores, dtype=float)
    orden = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[orden[j + 1]] == v[orden[i]]:
            j += 1
        r[orden[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def referencia_spearman(x, y):
    rx, ry = _rangos(x), _rangos(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    n = len(rx)
    t = rho * np.sqrt((n - 2) / (1 - rho ** 2))
    return rho, float(2 * stats.t.sf(abs(t), n - 2))


def referencia_kruskal(grupos):
    todos = np.concatenate(grupos)
    n = len(todos)
    r = _rangos(todos)
    h, inicio = 0.0, 0
    for g in grupos:
        h += r[inicio:inicio + len(g)].sum() ** 2 / len(g)
        inicio += len(g)
    h = 12 / (n * (n + 1)) * h - 3 * (n + 1)
    _, conteos = np.unique(todos, return_counts=True)
    h /= 1 - (conteos ** 3 - conteos).sum() / (n ** 3 - n)
    return float(h), float(stats.chi2.sf(h, len(grupos) - 1))


def test_cp16_coincide_con_calculo_de_referencia_independiente(aplicacion, capsys):
    codigos = crear_participantes(aplicacion, cantidad=40)
    cliente = aplicacion.test_client()
    iniciar_sesion(cliente)
    subir(cliente, csv_metricas(codigos))
    with aplicacion.app_context():
        ejecutar_emparejamiento()
        analisis = ejecutar_analisis()
        tabla = construir_tabla_emparejada(analisis.emparejamiento) if hasattr(analisis, "emparejamiento") else None
        if tabla is None:
            from servicios.analisis import ultimo_emparejamiento
            tabla = construir_tabla_emparejada(ultimo_emparejamiento())
        dif, comparaciones = 0.0, 0
        for c in analisis.correlaciones:
            rho, p = referencia_spearman(tabla[c.dimension], tabla[c.variable_rendimiento])
            dif = max(dif, abs(rho - c.coeficiente), abs(p - c.p_valor))
            comparaciones += 1
        for s in analisis.subgrupos:
            grupos = [g[s.variable_comparada].astype(float).to_numpy() for _, g in tabla.groupby(s.variable_agrupacion)
                      if len(g) >= aplicacion.config["MUESTRA_MINIMA_SUBGRUPO"]]
            h, p = referencia_kruskal(grupos)
            dif = max(dif, abs(h - s.estadistico), abs(p - s.p_valor))
            comparaciones += 1
    with capsys.disabled():
        print(f"\nCP-16: {comparaciones} resultados comparados; diferencia máxima = {dif:.2e}")
    assert comparaciones >= 30 and dif <= 0.001
