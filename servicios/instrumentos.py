"""Instrumentos de medición: BFI-44 (versión en español) y escala de autopercepción de rendimiento.

Calificación BFI-44 (John y Srivastava, 1999): cada ítem se responde de 1 (Totalmente en desacuerdo)
a 5 (Totalmente de acuerdo). Los ítems inversos se recodifican como 6 - valor. El puntaje de cada
dimensión es el promedio de sus ítems.
"""

OPCIONES_LIKERT = [
    (1, "Totalmente en desacuerdo"),
    (2, "En desacuerdo"),
    (3, "Ni de acuerdo ni en desacuerdo"),
    (4, "De acuerdo"),
    (5, "Totalmente de acuerdo"),
]

DIMENSIONES = {
    "apertura": "Apertura a la experiencia",
    "responsabilidad": "Responsabilidad",
    "extraversion": "Extraversión",
    "amabilidad": "Amabilidad",
    "neuroticismo": "Neuroticismo",
}
SIGLAS_DIMENSION = {"apertura": "O", "responsabilidad": "C", "extraversion": "E", "amabilidad": "A", "neuroticismo": "N"}

# (número, enunciado, dimensión, es_inverso)
ITEMS_BFI44 = [
    (1, "Es conversador, hablador", "extraversion", False),
    (2, "Tiende a ser criticón", "amabilidad", True),
    (3, "Es minucioso en el trabajo", "responsabilidad", False),
    (4, "Es depresivo, melancólico", "neuroticismo", False),
    (5, "Es original, se le ocurren ideas nuevas", "apertura", False),
    (6, "Es reservado", "extraversion", True),
    (7, "Es generoso y ayuda a los demás", "amabilidad", False),
    (8, "Puede ser algo descuidado", "responsabilidad", True),
    (9, "Es relajado, controla bien el estrés", "neuroticismo", True),
    (10, "Tiene intereses muy diversos", "apertura", False),
    (11, "Está lleno de energía", "extraversion", False),
    (12, "Inicia disputas con los demás", "amabilidad", True),
    (13, "Es un trabajador cumplidor, digno de confianza", "responsabilidad", False),
    (14, "Puede ser tenso", "neuroticismo", False),
    (15, "Es ingenioso, un pensador profundo", "apertura", False),
    (16, "Genera mucho entusiasmo", "extraversion", False),
    (17, "Tiende a ser perdonador", "amabilidad", False),
    (18, "Tiende a ser desorganizado", "responsabilidad", True),
    (19, "Se preocupa mucho", "neuroticismo", False),
    (20, "Tiene una imaginación activa", "apertura", False),
    (21, "Tiende a ser callado", "extraversion", True),
    (22, "Generalmente es confiado", "amabilidad", False),
    (23, "Tiende a ser flojo", "responsabilidad", True),
    (24, "Es emocionalmente estable, no se altera fácilmente", "neuroticismo", True),
    (25, "Es inventivo", "apertura", False),
    (26, "Tiene una personalidad enérgica", "extraversion", False),
    (27, "Puede ser frío y distante", "amabilidad", True),
    (28, "Persevera hasta terminar la tarea", "responsabilidad", False),
    (29, "Puede ser temperamental", "neuroticismo", False),
    (30, "Valora las experiencias artísticas y estéticas", "apertura", False),
    (31, "A veces es tímido, inhibido", "extraversion", True),
    (32, "Es considerado y amable con casi todos", "amabilidad", False),
    (33, "Hace las cosas eficientemente", "responsabilidad", False),
    (34, "Mantiene la calma en situaciones tensas", "neuroticismo", True),
    (35, "Prefiere el trabajo rutinario", "apertura", True),
    (36, "Es sociable, extrovertido", "extraversion", False),
    (37, "A veces es grosero con los demás", "amabilidad", True),
    (38, "Hace planes y los sigue", "responsabilidad", False),
    (39, "Se pone nervioso con facilidad", "neuroticismo", False),
    (40, "Le gusta reflexionar, jugar con las ideas", "apertura", False),
    (41, "Tiene pocos intereses artísticos", "apertura", True),
    (42, "Le gusta cooperar con los demás", "amabilidad", False),
    (43, "Se distrae con facilidad", "responsabilidad", True),
    (44, "Es sofisticado en arte, música o literatura", "apertura", False),
]

# Escala de autopercepción de rendimiento laboral (8 ítems Likert, todos directos).
# Instrumento de elaboración propia a validar con juicio de expertos y piloto (ver tesis).
ITEMS_ESCALA_RENDIMIENTO = [
    (1, "Cumplo con los compromisos que asumo en cada sprint."),
    (2, "Entrego un trabajo de calidad que requiere pocas correcciones."),
    (3, "Termino mis tareas dentro de los plazos acordados con el equipo."),
    (4, "Resuelvo con rapidez los problemas técnicos que se me presentan."),
    (5, "Mi trabajo contribuye de forma importante a los objetivos del equipo."),
    (6, "Colaboro de manera efectiva con mis compañeros para lograr resultados."),
    (7, "Mantengo un ritmo de trabajo constante a lo largo del sprint."),
    (8, "Estoy satisfecho con mi desempeño general en los últimos meses."),
]

TOTAL_ITEMS_BFI = len(ITEMS_BFI44)
TOTAL_ITEMS_ESCALA = len(ITEMS_ESCALA_RENDIMIENTO)


def valor_directo(valor_marcado: int, es_inverso: bool) -> int:
    """Aplica la recodificación de ítems inversos (RF-13)."""
    return 6 - valor_marcado if es_inverso else valor_marcado


def calcular_puntajes_bfi(respuestas: dict[int, int]) -> dict[str, float]:
    """Calcula los 5 puntajes (promedio de 1 a 5) a partir de {numero_item: valor}."""
    if len(respuestas) != TOTAL_ITEMS_BFI:
        raise ValueError("Se requieren las 44 respuestas del BFI-44.")
    acumulado: dict[str, list[int]] = {dimension: [] for dimension in DIMENSIONES}
    for numero, _, dimension, es_inverso in ITEMS_BFI44:
        acumulado[dimension].append(valor_directo(respuestas[numero], es_inverso))
    return {dimension: round(sum(v) / len(v), 4) for dimension, v in acumulado.items()}


def calcular_rendimiento_autopercibido(respuestas: dict[int, int]) -> float:
    if len(respuestas) != TOTAL_ITEMS_ESCALA:
        raise ValueError("Se requieren todas las respuestas de la escala de rendimiento.")
    return round(sum(respuestas.values()) / len(respuestas), 4)
