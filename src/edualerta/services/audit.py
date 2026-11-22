"""Bitácora de auditoría (F75): quién hizo qué, sobre qué y cuándo.

Se escribe en MongoDB (`auditoria`). Si MongoDB no responde, el evento se guarda en un
archivo JSONL local para no perder trazabilidad (F82) y se muestra junto con los demás.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import pandas as pd
from pymongo.errors import PyMongoError

from edualerta import config
from edualerta.db import mongo

_logger = logging.getLogger(__name__)


def _fallback_path():
    return config.sqlite_path().parent / "auditoria_local.jsonl"


def log_event(usuario: str, accion: str, entidad: str, entidad_id: str | None = None,
              detalle: dict | None = None, perfil: str | None = None) -> None:
    event = {"fecha": datetime.now().replace(microsecond=0), "usuario": usuario, "perfil": perfil,
             "accion": accion, "entidad": entidad, "entidad_id": entidad_id, "detalle": detalle or {}}
    try:
        mongo.get_db().auditoria.insert_one(dict(event))
    except PyMongoError as exc:
        _logger.warning("Auditoría en respaldo local (MongoDB no disponible): %s", exc)
        path = _fallback_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**event, "fecha": event["fecha"].isoformat(), "respaldo_local": True},
                                ensure_ascii=False, default=str) + "\n")


# Alias corto usado por el resto de servicios
log = log_event


def events(limit: int = 500, usuario: str | None = None, accion: str | None = None) -> pd.DataFrame:
    q = {}
    if usuario:
        q["usuario"] = usuario
    if accion:
        q["accion"] = accion
    rows = []
    try:
        rows = list(mongo.get_db().auditoria.find(q, {"_id": 0}).sort("fecha", -1).limit(limit))
    except PyMongoError:
        pass
    path = _fallback_path()
    if path.exists():
        for line in path.read_text("utf-8").splitlines():
            ev = json.loads(line)
            if all(ev.get(k) == v for k, v in q.items()):
                ev["fecha"] = datetime.fromisoformat(ev["fecha"])
                rows.append(ev)
    if not rows:
        return pd.DataFrame(columns=["fecha", "usuario", "perfil", "accion", "entidad", "entidad_id", "detalle"])
    df = pd.DataFrame(rows).sort_values("fecha", ascending=False).head(limit)
    df["detalle"] = df["detalle"].map(lambda d: json.dumps(d, ensure_ascii=False, default=str))
    return df


def clear_fallback() -> None:
    path = _fallback_path()
    if path.exists():
        path.unlink()
