"""Crea (o actualiza la contraseña de) la cuenta de la investigadora.

Uso:  python scripts/crear_investigadora.py usuario
La contraseña se solicita por teclado y se guarda como hash bcrypt (nunca en texto plano).
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_aplicacion
from modelos import Usuario, bd
from servicios.autenticacion import crear_hash, crear_usuario


def principal() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/crear_investigadora.py <usuario>")
    nombre_usuario = sys.argv[1].strip()
    contrasena = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if contrasena != getpass.getpass("Repita la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    with crear_aplicacion().app_context():
        existente = Usuario.query.filter_by(usuario=nombre_usuario).first()
        try:
            if existente:
                if len(contrasena) < 8:
                    raise ValueError("La contraseña debe tener al menos 8 caracteres.")
                existente.hash_contrasena = crear_hash(contrasena)
                existente.intentos_fallidos, existente.bloqueado_hasta = 0, None
                bd.session.commit()
                print(f"Contraseña actualizada para «{nombre_usuario}».")
            else:
                crear_usuario(nombre_usuario, contrasena)
                print(f"Cuenta «{nombre_usuario}» creada.")
        except ValueError as error:
            sys.exit(str(error))


if __name__ == "__main__":
    principal()
