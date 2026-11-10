"""Autenticación de la investigadora (CU8, RF-25 a RF-27, RNF-07, RNF-20)."""
from datetime import datetime, timedelta

import bcrypt
from flask import current_app

from modelos import Sesion, Usuario, bd

MENSAJE_GENERICO = "Usuario o contraseña incorrectos."  # no revela cuál dato falló (RF-27)


def crear_hash(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(contrasena.encode(), hash_guardado.encode())
    except ValueError:
        return False


def crear_usuario(nombre_usuario: str, contrasena: str) -> Usuario:
    if len(contrasena) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    usuario = Usuario(usuario=nombre_usuario.strip(), hash_contrasena=crear_hash(contrasena))
    bd.session.add(usuario)
    bd.session.commit()
    return usuario


def intentar_ingreso(nombre_usuario: str, contrasena: str) -> tuple[Sesion | None, str | None]:
    """Devuelve (sesión, None) si ingresa; (None, mensaje) si se rechaza."""
    ahora = datetime.now()
    usuario = Usuario.query.filter_by(usuario=(nombre_usuario or "").strip()).first()

    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        minutos = int((usuario.bloqueado_hasta - ahora).total_seconds() // 60) + 1
        return None, f"Ingreso bloqueado temporalmente por intentos fallidos. Intente de nuevo en {minutos} minuto(s)."

    if usuario and verificar_contrasena(contrasena or "", usuario.hash_contrasena):
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        sesion = Sesion(id_usuario=usuario.id_usuario, fecha_inicio=ahora, ultima_actividad=ahora)
        bd.session.add(sesion)
        bd.session.commit()
        return sesion, None

    if usuario:
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= current_app.config["MAX_INTENTOS_FALLIDOS"]:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=current_app.config["MINUTOS_BLOQUEO"])
            usuario.intentos_fallidos = 0
            bd.session.commit()
            return None, (f"Se superó el máximo de intentos. El ingreso quedó bloqueado "
                          f"{current_app.config['MINUTOS_BLOQUEO']} minutos.")
        bd.session.commit()
    return None, MENSAJE_GENERICO


def sesion_vigente(id_sesion: int | None) -> Sesion | None:
    """Devuelve la sesión si sigue activa; la cierra por inactividad si venció (RF-26)."""
    if not id_sesion:
        return None
    sesion = bd.session.get(Sesion, id_sesion)
    if sesion is None or sesion.fecha_cierre is not None:
        return None
    ahora = datetime.now()
    limite = timedelta(minutes=current_app.config["MINUTOS_INACTIVIDAD_SESION"])
    if ahora - sesion.ultima_actividad > limite:
        sesion.fecha_cierre, sesion.motivo_cierre = ahora, "inactividad"
        bd.session.commit()
        return None
    sesion.ultima_actividad = ahora
    bd.session.commit()
    return sesion


def cerrar_sesion(id_sesion: int | None) -> None:
    sesion = bd.session.get(Sesion, id_sesion) if id_sesion else None
    if sesion and sesion.fecha_cierre is None:
        sesion.fecha_cierre, sesion.motivo_cierre = datetime.now(), "manual"
        bd.session.commit()
