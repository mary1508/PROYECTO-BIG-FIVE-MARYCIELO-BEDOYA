"""Genera datos SIMULADOS para probar la plataforma de punta a punta.

Crea participantes ficticios (con correlaciones leves entre personalidad y rendimiento), guarda sus respuestas
y escribe archivos CSV de métricas en la carpeta «ejemplos». Los datos NO son reales: no los use en la tesis.

Uso:  python scripts/generar_datos_demo.py [cantidad_por_equipo]
"""
import csv
import os
import random
import sys

CARPETA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CARPETA_RAIZ)

from app import crear_aplicacion
from modelos import EquipoDesarrollo, ROLES, bd
from servicios import formulario
from servicios.instrumentos import ITEMS_BFI44, TOTAL_ITEMS_ESCALA

SEMILLA = 2026


def limitar(valor: float, minimo: int = 1, maximo: int = 5) -> int:
    return max(minimo, min(maximo, round(valor)))


def respuestas_bfi_simuladas(rasgos: dict[str, float], azar: random.Random) -> dict[int, int]:
    """Genera marcas coherentes con un nivel latente por dimensión (considera ítems inversos)."""
    respuestas = {}
    for numero, _, dimension, es_inverso in ITEMS_BFI44:
        objetivo = rasgos[dimension] + azar.gauss(0, 0.8)
        respuestas[numero] = limitar(6 - objetivo if es_inverso else objetivo)
    return respuestas


def principal() -> None:
    por_equipo = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    azar = random.Random(SEMILLA)
    os.makedirs(os.path.join(CARPETA_RAIZ, "ejemplos"), exist_ok=True)
    aplicacion = crear_aplicacion()
    with aplicacion.app_context():
        for equipo in EquipoDesarrollo.query.order_by(EquipoDesarrollo.id_equipo).all():
            filas = []
            for _ in range(por_equipo):
                rol = azar.choices(ROLES, weights=[55, 20, 10, 15])[0]
                anios = max(0, int(azar.gauss(5, 3.5)))
                rasgos = {d: min(5, max(1, azar.gauss(3.4, 0.7))) for d in
                          ("apertura", "responsabilidad", "extraversion", "amabilidad", "neuroticismo")}
                desempeno = (0.5 * (rasgos["responsabilidad"] - 3.4) - 0.3 * (rasgos["neuroticismo"] - 3.4)
                             + 0.12 * min(anios, 10) + azar.gauss(0, 0.6))

                participante = formulario.registrar_participante(equipo, rol, anios)
                formulario.guardar_bfi44(participante, respuestas_bfi_simuladas(rasgos, azar))
                escala = {n: limitar(3.5 + desempeno * 0.6 + azar.gauss(0, 0.7)) for n in range(1, TOTAL_ITEMS_ESCALA + 1)}
                formulario.guardar_escala_y_finalizar(participante, escala)

                filas.append([
                    participante.codigo_anonimo,
                    max(1, round(14 + desempeno * 5 + azar.gauss(0, 3))),
                    max(1, round(30 + desempeno * 10 + azar.gauss(0, 6))),
                    max(0, round(4 + desempeno * 1.5 + azar.gauss(0, 1.5))),
                    round(max(0.5, 4.5 - desempeno * 0.8 + azar.gauss(0, 0.8)), 1),
                ])
            nombre = f"metricas_demo_equipo_{equipo.id_equipo}.csv"
            with open(os.path.join(CARPETA_RAIZ, "ejemplos", nombre), "w", newline="", encoding="utf-8") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(["codigo_anonimo", "issues_completados", "story_points", "bugs_resueltos", "tiempo_ciclo_dias"])
                escritor.writerows(filas)
            print(f"Equipo {equipo.id_equipo} ({equipo.nombre}): {len(filas)} participantes → ejemplos/{nombre}")
        print("Listo. Cargue cada CSV en Panel → Reportes (periodo de 60–90 días) y luego empareje y analice.")


if __name__ == "__main__":
    principal()
