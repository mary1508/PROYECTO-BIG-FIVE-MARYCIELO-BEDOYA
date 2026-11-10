"""Configuración compartida de las pruebas: base de datos temporal y cliente HTTP."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_aplicacion
from configuracion import Configuracion
from servicios.autenticacion import crear_usuario


@pytest.fixture
def aplicacion(tmp_path):
    class ConfiguracionPrueba(Configuracion):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(tmp_path / "prueba.db")
        MUESTRA_MINIMA_EMPAREJADOS = 10
        MUESTRA_MINIMA_SUBGRUPO = 3

    app = crear_aplicacion(ConfiguracionPrueba)
    with app.app_context():
        crear_usuario("investigadora", "clave-segura-1")
    return app


@pytest.fixture
def cliente(aplicacion):
    return aplicacion.test_client()


def extraer_token(cliente, ruta="/") -> str:
    html = cliente.get(ruta).get_data(as_text=True)
    coincidencia = re.search(r'name="token_csrf" value="([^"]+)"', html)
    return coincidencia.group(1) if coincidencia else ""


def iniciar_sesion(cliente, usuario="investigadora", contrasena="clave-segura-1"):
    token = extraer_token(cliente, "/admin/ingreso")
    return cliente.post("/admin/ingreso", data={"usuario": usuario, "contrasena": contrasena, "token_csrf": token})
