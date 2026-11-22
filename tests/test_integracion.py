"""Integración SQL + MongoDB real + dashboard Streamlit (F26-F28, F84).

* Las pruebas `integration` corren contra el MongoDB del docker-compose (se omiten si no hay conexión).
* Las pruebas de dashboard ejecutan las pantallas reales con streamlit.testing (AppTest).
"""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from edualerta.db import sql
from edualerta.etl import pipeline
from edualerta.services import auth, followup, kpi

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.mark.integration
def test_sql_mongo_roundtrip_real(real_mongo):
    out = pipeline.run(trigger="test_integracion")
    assert out["estado"] == "exitosa", out["errores"]
    conn = sql.connect()
    db = real_mongo
    # F26: crear, leer y actualizar en MongoDB real; F27: vínculo por código anónimo
    oid = followup.add_observation(db, "E-0042", "Observación de prueba de integración", "observacion", "alison")
    followup.update_observation(db, oid, "Observación corregida", "alison")
    perfil = followup.student_profile(conn, db, "E-0042")
    assert any(o["texto"] == "Observación corregida" for o in perfil["observaciones"])
    assert not perfil["indicadores"].empty                                     # F28: SQL + Mongo juntos
    sql_codes = {r[0] for r in conn.execute("SELECT codigo FROM estudiantes")}
    assert set(db.alertas.distinct("estudiante_codigo")) <= sql_codes
    k = kpi.compute(conn, db, "2025-T3", sql.get_rules(conn))
    assert k["alertas_prioritarias"]["valor"] > 0
    # índice único = idempotencia en Mongo real
    pipeline.run(trigger="test_integracion", force=True)
    assert db.alertas.count_documents({}) == len(db.alertas.distinct("_id"))
    conn.close()


def _login(at: AppTest, usuario: str):
    import edualerta.config as cfg
    u = auth.authenticate(usuario, cfg.demo_password())
    at.session_state["user"] = u
    return at


VIEWS = [("inicio.py", "nathalia"), ("datos.py", "german"), ("seguimiento.py", "alison"),
         ("tecnologia.py", "german"), ("regiones.py", "nathalia"), ("analisis.py", "nathalia"),
         ("decisiones.py", "nathalia"), ("administracion.py", "german")]


@pytest.mark.parametrize("view,usuario", VIEWS)
def test_dashboard_views_render(loaded, view, usuario):
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    at = _login(AppTest.from_file(str(APP / "views" / view), default_timeout=60), usuario)
    at.run()
    assert not at.exception, at.exception


def test_access_is_restricted_by_profile(loaded):
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    at = _login(AppTest.from_file(str(APP / "views" / "seguimiento.py"), default_timeout=60), "german")
    at.run()
    assert any("no tiene acceso" in e.value for e in at.error)


def test_filter_changes_kpis(loaded):
    """F60: al cambiar el filtro de centro cambian los indicadores mostrados."""
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    at = _login(AppTest.from_file(str(APP / "views" / "inicio.py"), default_timeout=60), "nathalia")
    at.run()

    def band():
        return next(m.value for m in at.markdown if "Tasa de asistencia" in m.value)

    before = band()
    at.multiselect(key="f_centros").set_value(["CE-005"]).run()
    assert not at.exception
    assert band() != before
