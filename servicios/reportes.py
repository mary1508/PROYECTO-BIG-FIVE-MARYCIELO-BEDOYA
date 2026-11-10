"""Servicio de carga de reportes de métricas exportados de Jira o Azure DevOps (CU3, RF-08 a RF-10)."""
import io
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from modelos import EquipoDesarrollo, MetricaRendimiento, ReporteMetricas, bd

COLUMNAS_ESPERADAS = ["codigo_anonimo", "issues_completados", "story_points", "bugs_resueltos", "tiempo_ciclo_dias"]

# Nombres alternativos comunes en exportaciones de Jira y Azure DevOps (RNF-16).
ALIAS_COLUMNAS = {
    "codigo_anonimo": {"codigo_anonimo", "codigo", "code", "anonymous_code", "codigo_participante"},
    "issues_completados": {"issues_completados", "issues_completed", "completed_issues", "items_completados",
                           "work_items_completed", "tareas_completadas"},
    "story_points": {"story_points", "story_points_completed", "puntos_historia", "puntos_de_historia", "completed_story_points",
                     "storypoints", "effort_completed"},
    "bugs_resueltos": {"bugs_resueltos", "bugs_resolved", "resolved_bugs", "bugs_cerrados", "bugs_closed"},
    "tiempo_ciclo_dias": {"tiempo_ciclo_dias", "tiempo_ciclo", "cycle_time", "cycle_time_days", "cycle_time_dias"},
}

TEXTO_PLANTILLA = (
    "codigo_anonimo,issues_completados,story_points,bugs_resueltos,tiempo_ciclo_dias\n"
    "BF-ABC234,18,34,5,3.2\nBF-XYZ567,12,21,3,4.1\n"
)


@dataclass
class ResultadoCarga:
    exito: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    registros_procesados: int = 0
    reporte: ReporteMetricas | None = None


def _normalizar(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.strip().lower()).strip("_")


def leer_archivo(nombre: str, contenido: bytes, extensiones_permitidas: set[str]) -> tuple[pd.DataFrame | None, str | None]:
    """Valida la extensión y lee el archivo en memoria (no se guarda en disco)."""
    extension = os.path.splitext(nombre or "")[1].lower()
    if extension not in extensiones_permitidas:
        return None, f"Formato no soportado («{extension or 'sin extensión'}»). Use un archivo .csv o .xlsx."
    try:
        if extension == ".csv":
            try:
                tabla = pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding="utf-8-sig")
            except UnicodeDecodeError:
                tabla = pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding="latin-1")
        else:
            tabla = pd.read_excel(io.BytesIO(contenido), engine="openpyxl")
    except Exception:
        return None, "No se pudo leer el archivo. Verifique que no esté dañado y que sea un CSV o Excel válido."
    if tabla.empty:
        return None, "El archivo no contiene filas de datos."
    return tabla, None


def estandarizar_columnas(tabla: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Renombra columnas a los nombres esperados. Devuelve (tabla, columnas faltantes)."""
    renombres = {}
    for columna in tabla.columns:
        normal = _normalizar(columna)
        for oficial, alias in ALIAS_COLUMNAS.items():
            if normal in alias:
                renombres[columna] = oficial
                break
    tabla = tabla.rename(columns=renombres)
    faltantes = [c for c in COLUMNAS_ESPERADAS if c not in tabla.columns]
    return tabla, faltantes


def validar_filas(tabla: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Valida tipos y valores. Devuelve la tabla limpia y la lista de errores (vacía si todo está bien)."""
    errores = []
    tabla = tabla[COLUMNAS_ESPERADAS].copy()
    tabla["codigo_anonimo"] = tabla["codigo_anonimo"].astype(str).str.strip().str.upper()
    vacios = tabla["codigo_anonimo"].isin(["", "NAN", "NONE"])
    if vacios.any():
        errores.append(f"Hay {int(vacios.sum())} fila(s) sin código anónimo (filas {_filas(tabla, vacios)}).")
    duplicados = tabla["codigo_anonimo"].duplicated(keep=False) & ~vacios
    if duplicados.any():
        codigos = ", ".join(sorted(tabla.loc[duplicados, "codigo_anonimo"].unique())[:5])
        errores.append(f"Códigos duplicados en el archivo: {codigos}. Cada código debe aparecer una sola vez.")
    for columna in COLUMNAS_ESPERADAS[1:]:
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")
        invalidos = tabla[columna].isna()
        negativos = tabla[columna] < 0
        if invalidos.any():
            errores.append(f"La columna «{columna}» tiene valores no numéricos o vacíos (filas {_filas(tabla, invalidos)}).")
        elif negativos.any():
            errores.append(f"La columna «{columna}» tiene valores negativos (filas {_filas(tabla, negativos)}).")
    return tabla, errores


def _filas(tabla: pd.DataFrame, mascara) -> str:
    numeros = [str(i + 2) for i in tabla.index[mascara].tolist()[:5]]  # +2: encabezado + base 1
    return ", ".join(numeros) + ("…" if mascara.sum() > 5 else "")


def validar_periodo(inicio_texto: str, fin_texto: str) -> tuple[date | None, date | None, str | None]:
    try:
        inicio = datetime.strptime(inicio_texto, "%Y-%m-%d").date()
        fin = datetime.strptime(fin_texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None, None, "Indique las fechas de inicio y fin del periodo."
    if fin < inicio:
        return None, None, "La fecha de fin no puede ser anterior a la de inicio."
    dias = (fin - inicio).days + 1
    if dias < 14 or dias > 120:
        return inicio, fin, "El periodo debe cubrir entre 2 y 3 sprints (aprox. 60–90 días); se aceptan de 14 a 120 días."
    return inicio, fin, None


def procesar_reporte(id_equipo, inicio_texto, fin_texto, nombre_archivo, contenido, id_usuario,
                     extensiones_permitidas) -> ResultadoCarga:
    """Flujo completo de CU3. Ante cualquier error rechaza la carga completa (RF-10)."""
    resultado = ResultadoCarga(exito=False)
    equipo = bd.session.get(EquipoDesarrollo, int(id_equipo)) if str(id_equipo).isdigit() else None
    if equipo is None:
        resultado.errores.append("Seleccione el equipo al que pertenece el reporte.")
    inicio, fin, error_periodo = validar_periodo(inicio_texto, fin_texto)
    if error_periodo:
        resultado.errores.append(error_periodo)
    if not nombre_archivo or not contenido:
        resultado.errores.append("Seleccione el archivo exportado de Jira o Azure DevOps.")
    if resultado.errores:
        return resultado

    tabla, error_lectura = leer_archivo(nombre_archivo, contenido, extensiones_permitidas)
    if error_lectura:
        resultado.errores.append(error_lectura)
        return resultado
    tabla, faltantes = estandarizar_columnas(tabla)
    if faltantes:
        resultado.errores.append("Faltan columnas obligatorias: " + ", ".join(faltantes) + ".")
        return resultado
    tabla, errores_filas = validar_filas(tabla)
    if errores_filas:
        resultado.errores.extend(errores_filas)
        return resultado

    reporte = ReporteMetricas(
        id_equipo=equipo.id_equipo, id_usuario=id_usuario, periodo_inicio=inicio, periodo_fin=fin,
        nombre_archivo=os.path.basename(nombre_archivo)[:120],
        formato=os.path.splitext(nombre_archivo)[1].lower().lstrip(".").upper(),
        registros_procesados=len(tabla),
    )
    for fila in tabla.itertuples(index=False):
        reporte.metricas.append(MetricaRendimiento(
            codigo_anonimo=fila.codigo_anonimo, issues_completados=int(fila.issues_completados),
            story_points=float(fila.story_points), bugs_resueltos=int(fila.bugs_resueltos),
            tiempo_ciclo_dias=float(fila.tiempo_ciclo_dias),
        ))
    bd.session.add(reporte)
    bd.session.commit()
    resultado.exito = True
    resultado.registros_procesados = len(tabla)
    resultado.reporte = reporte
    return resultado
