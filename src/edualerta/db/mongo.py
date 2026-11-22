"""Persistencia documental MongoDB (F25-F27).

Colecciones: observaciones, alertas, casos, intervenciones, decisiones, auditoria.
Todas usan el código anónimo del estudiante definido en SQL (`estudiante_codigo`).
"""
from __future__ import annotations

import logging
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from edualerta import config

log = logging.getLogger(__name__)

COLLECTIONS = ["observaciones", "alertas", "casos", "intervenciones", "decisiones", "auditoria"]

_override_db: Database | None = None


class MongoUnavailable(RuntimeError):
    """MongoDB no responde; la app debe degradarse sin caerse (F82)."""


def use_database(db: Database | None) -> None:
    """Permite inyectar una base (p. ej. mongomock en pruebas)."""
    global _override_db
    _override_db = db
    _client.cache_clear()


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    return MongoClient(config.mongo_uri(), serverSelectionTimeoutMS=4000, connectTimeoutMS=4000,
                       tz_aware=False)


def get_db() -> Database:
    if _override_db is not None:
        return _override_db
    return _client()[config.mongo_db_name()]


def _ping(db: Database) -> None:
    try:
        db.command("ping")
    except NotImplementedError:  # mongomock en pruebas
        db.list_collection_names()


def ping() -> bool:
    try:
        _ping(get_db())
        return True
    except PyMongoError as exc:
        log.warning("MongoDB no disponible: %s", exc)
        return False


def require() -> Database:
    db = get_db()
    try:
        _ping(db)
    except PyMongoError as exc:
        raise MongoUnavailable(str(exc)) from exc
    return db


def ensure_indexes(db: Database | None = None) -> None:
    """Índices únicos = claves de idempotencia para re-ejecuciones del pipeline."""
    db = db if db is not None else get_db()
    db.alertas.create_index([("estudiante_codigo", ASCENDING), ("periodo_codigo", ASCENDING)], unique=True)
    db.alertas.create_index([("nivel", ASCENDING), ("estado", ASCENDING)])
    db.observaciones.create_index([("estudiante_codigo", ASCENDING), ("fecha", DESCENDING)])
    db.casos.create_index("alerta_id", unique=True)
    db.casos.create_index([("estudiante_codigo", ASCENDING), ("estado", ASCENDING)])
    db.intervenciones.create_index([("caso_id", ASCENDING), ("fecha", ASCENDING)])
    db.intervenciones.create_index("estudiante_codigo")
    db.decisiones.create_index("regla_clave", unique=True)
    db.auditoria.create_index([("fecha", DESCENDING)])


def reset(db: Database | None = None) -> None:
    db = db if db is not None else get_db()
    for name in COLLECTIONS:
        db[name].delete_many({})
    ensure_indexes(db)
