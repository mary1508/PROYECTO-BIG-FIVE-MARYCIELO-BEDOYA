"""Configuración central de la plataforma."""
import os
from datetime import timedelta

CARPETA_BASE = os.path.abspath(os.path.dirname(__file__))


class Configuracion:
    # En producción defina la variable de entorno CLAVE_SECRETA con un valor largo y aleatorio.
    SECRET_KEY = os.environ.get("CLAVE_SECRETA", "cambie-esta-clave-en-produccion")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "URL_BASE_DATOS", "sqlite:///" + os.path.join(CARPETA_BASE, "bigfive.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cookies de sesión seguras (RNF-06 / RNF-07). Active COOKIE_SEGURA=1 cuando use HTTPS.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SEGURA", "0") == "1"

    # Carga de archivos (RF-08): máximo 5 MB.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    EXTENSIONES_PERMITIDAS = {".csv", ".xlsx"}

    # Control de acceso (RF-26, RF-27)
    MINUTOS_INACTIVIDAD_SESION = 30
    MAX_INTENTOS_FALLIDOS = 5
    MINUTOS_BLOQUEO = 5

    # Análisis estadístico (RF-17)
    MUESTRA_MINIMA_EMPAREJADOS = 30
    MUESTRA_MINIMA_SUBGRUPO = 5
    NIVEL_SIGNIFICANCIA = 0.05

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=MINUTOS_INACTIVIDAD_SESION)
