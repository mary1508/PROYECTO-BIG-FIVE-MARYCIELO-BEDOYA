from servicios.instrumentos import (
    ITEMS_BFI44, TOTAL_ITEMS_BFI, calcular_puntajes_bfi, calcular_rendimiento_autopercibido, valor_directo,
)
import pytest


def test_hay_44_items_con_distribucion_oficial():
    assert TOTAL_ITEMS_BFI == 44
    cuenta = {}
    for _, _, dimension, _ in ITEMS_BFI44:
        cuenta[dimension] = cuenta.get(dimension, 0) + 1
    assert cuenta == {"extraversion": 8, "amabilidad": 9, "responsabilidad": 9, "neuroticismo": 8, "apertura": 10}


def test_items_inversos_se_recodifican():
    assert valor_directo(1, True) == 5
    assert valor_directo(2, False) == 2


def test_todo_en_tres_da_promedio_tres():
    puntajes = calcular_puntajes_bfi({n: 3 for n in range(1, 45)})
    assert all(v == 3 for v in puntajes.values())


def test_respuesta_maxima_en_items_directos_e_inversos():
    # Marcar 5 en todo: directos suman 5 e inversos 1, así que los promedios quedan entre 1 y 5.
    puntajes = calcular_puntajes_bfi({n: 5 for n in range(1, 45)})
    assert puntajes["extraversion"] == pytest.approx((5 * 5 + 1 * 3) / 8, abs=1e-3)  # 3 ítems inversos
    assert all(1 <= v <= 5 for v in puntajes.values())


def test_exige_44_respuestas():
    with pytest.raises(ValueError):
        calcular_puntajes_bfi({1: 3})


def test_rendimiento_promedio():
    assert calcular_rendimiento_autopercibido({n: 4 for n in range(1, 9)}) == 4
