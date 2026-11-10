# Plataforma de análisis Big Five – rendimiento laboral

Aplicación web (Flask + SQLite) para la tesis sobre la relación entre los rasgos de personalidad (BFI-44) y el
rendimiento de equipos de desarrollo (D&T Integra y Paulonia).

## Módulos
| Módulo | Qué hace | Casos de uso |
|---|---|---|
| Formulario público | Consentimiento, perfil, BFI-44 (44 ítems) y escala de rendimiento, con código anónimo | CU1, CU2 |
| Carga de reportes | Valida y carga CSV/Excel de Jira o Azure DevOps, con plantilla de referencia | CU4 |
| Emparejamiento | Cruza formulario y métricas solo por código anónimo; excluye códigos sin coincidencia | CU5 |
| Análisis | Correlación de Spearman; Kruskal-Wallis por rol y experiencia | CU6 |
| Dashboard | Gráficos, filtros, resaltado de p < 0,05, exportación a PNG y PDF | CU7 |
| Acceso | Usuario y contraseña (bcrypt), sesión de 30 min, bloqueo tras 5 intentos | CU8 |

## Puesta en marcha
```bash
pip install -r requirements.txt
python scripts/crear_investigadora.py mi_usuario      # pide la contraseña (mín. 8 caracteres)
python app.py                                          # http://127.0.0.1:5000
```
- Formulario de participantes: `http://127.0.0.1:5000/`
- Panel de la investigadora: `http://127.0.0.1:5000/admin/`

Variables de entorno opcionales: `CLAVE_SECRETA` (obligatoria en producción), `URL_BASE_DATOS`, `COOKIE_SEGURA=1` (con HTTPS).

## Probar con datos simulados
```bash
python scripts/generar_datos_demo.py 20     # 20 participantes ficticios por equipo + CSV en ejemplos/
```
Luego, en el panel: **Reportes** (cargue cada CSV, periodo de 60–90 días) → **Emparejamiento** → **Análisis** → **Dashboard**.
Los datos simulados no son reales: borre `bigfive.db` antes de la recolección verdadera.

## Formato del reporte de métricas
Columnas: `codigo_anonimo, issues_completados, story_points, bugs_resueltos, tiempo_ciclo_dias` (una fila por participante).
Se aceptan alias comunes de Jira/Azure DevOps (ver `servicios/reportes.py`).

## Pruebas
```bash
python -m pytest pruebas -q        # 32 pruebas: instrumentos, flujo completo, casos CP-04/10/15/16 y no funcionales
```
Para las pruebas CP-18 y CP-19 del dashboard (Playwright y Chromium), con el servidor en marcha y datos simulados cargados:
```bash
python scripts/prueba_navegador.py ejemplos carpeta_salida
```

## Estructura
```
app.py · configuracion.py · modelos.py · esquema_bd.sql
servicios/   instrumentos, formulario, reportes, emparejamiento, analisis, autenticacion
rutas/       participante (público) y administracion (con sesión)
plantillas/  participante/, admin/, componentes/
estatico/    css/estilos.css, js/ (cuestionario, dashboard, Chart.js local)
scripts/     crear_investigadora.py, generar_datos_demo.py
pruebas/     instrumentos y flujo completo
```

## Ajustes que debe validar con su asesor
- **Escala de rendimiento (8 ítems):** el texto está en `servicios/instrumentos.py`; reemplácelo por el instrumento aprobado en la tesis.
- **Muestra mínima:** 30 emparejados y 5 por subgrupo (`configuracion.py`); ajústelo al diseño muestral.
- **Rendimiento:** cada dimensión se correlaciona con la autopercepción y con cada métrica objetiva por separado.
- **Modelo de datos:** añade campos al ER (por ejemplo `variable_rendimiento` en las correlaciones y `motivo_cierre` en la sesión).
