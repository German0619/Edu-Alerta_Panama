"""Fixtures: cada sesión de pruebas usa SQLite temporal, archivos generados en tmp y mongomock.

Las pruebas marcadas `integration` usan un MongoDB real (MONGO_URI) con una base `*_test`
que se elimina al terminar; se omiten si MongoDB no responde.
"""
from __future__ import annotations

import os

import mongomock
import pytest

from edualerta import config, datagen
from edualerta.db import mongo, sql
from edualerta.etl import pipeline


def _isolate(mp: pytest.MonkeyPatch, base) -> None:
    mp.setenv("SQLITE_PATH", str(base / "db" / "edualerta_test.db"))
    mp.setattr(config, "RAW_DIR", base / "raw")
    mp.setattr(config, "DEMO_DIR", base / "demo")
    mp.setattr(config, "INCOMING_DIR", base / "incoming")
    datagen.generate(base / "raw", base / "demo")


@pytest.fixture
def mdb():
    prev = mongo._override_db
    db = mongomock.MongoClient()["edualerta_unit"]
    mongo.use_database(db)
    mongo.ensure_indexes(db)
    yield db
    mongo.use_database(prev)


@pytest.fixture(scope="session")
def loaded(tmp_path_factory):
    """Escenario base procesado una sola vez (solo lectura en las pruebas que lo usan)."""
    mp = pytest.MonkeyPatch()
    base = tmp_path_factory.mktemp("base")
    _isolate(mp, base)
    db = mongomock.MongoClient()["edualerta_session"]
    mongo.use_database(db)
    mongo.ensure_indexes(db)
    summary = pipeline.run(trigger="test")
    conn = sql.connect()
    yield {"conn": conn, "db": db, "summary": summary, "base": base}
    conn.close()
    mongo.use_database(None)
    mp.undo()


@pytest.fixture
def fresh(tmp_path, monkeypatch, mdb):
    """Escenario independiente para pruebas que modifican datos."""
    _isolate(monkeypatch, tmp_path)
    summary = pipeline.run(trigger="test")
    conn = sql.connect()
    yield {"conn": conn, "db": mdb, "summary": summary, "base": tmp_path}
    conn.close()


@pytest.fixture
def real_mongo(tmp_path, monkeypatch):
    name = os.environ.get("MONGO_DB", "edualerta")
    if not name.endswith("test"):
        name = f"{name}_test"
    monkeypatch.setenv("MONGO_DB", name)
    prev = mongo._override_db
    mongo.use_database(None)
    if not mongo.ping():
        mongo.use_database(prev)
        pytest.skip("MongoDB real no disponible")
    db = mongo.get_db()
    db.client.drop_database(name)
    mongo.ensure_indexes(db)
    _isolate(monkeypatch, tmp_path)
    yield db
    db.client.drop_database(name)
    mongo.use_database(prev)
