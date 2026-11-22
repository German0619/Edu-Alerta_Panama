"""Perfiles de uso y control de acceso demostrativo (F72, F73)."""
from __future__ import annotations

import hmac

from edualerta import config

PAGINAS = {
    "inicio": "Inicio",
    "datos": "Datos y ETL",
    "seguimiento": "Seguimiento",
    "tecnologia": "Tecnología escolar",
    "regiones": "Regiones",
    "analisis": "Análisis",
    "decisiones": "Decisiones",
    "administracion": "Administración",
}


def users() -> list[dict]:
    return config.settings()["usuarios"]


def profiles() -> dict:
    return config.settings()["perfiles"]


def authenticate(usuario: str, password: str) -> dict | None:
    for u in users():
        if u["usuario"] == usuario and hmac.compare_digest(password.encode(), config.demo_password().encode()):
            prof = profiles()[u["perfil"]]
            return {**u, "perfil_nombre": prof["nombre"], "paginas": prof["paginas"], "acciones": prof["acciones"]}
    return None


def can(user: dict | None, accion: str) -> bool:
    return bool(user) and accion in user.get("acciones", [])


def can_view(user: dict | None, pagina: str) -> bool:
    return bool(user) and pagina in user.get("paginas", [])


def permission_matrix() -> list[dict]:
    rows = []
    for key, prof in profiles().items():
        rows.append({"perfil": prof["nombre"],
                     **{PAGINAS[p]: ("✔" if p in prof["paginas"] else "—") for p in PAGINAS},
                     "acciones": ", ".join(prof["acciones"])})
    return rows
