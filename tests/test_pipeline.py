"""Pruebas del pipeline completo sobre los datos sintéticos (F14-F22, F27, F81, F83)."""
from edualerta.db import sql
from edualerta.etl import pipeline
from edualerta.services import kpi, masters, quality


def test_pipeline_runs_and_rejects_bad_records(loaded):
    s = loaded["summary"]
    assert s["estado"] == "exitosa", s["errores"]
    assert s["aceptados"] > 50_000 and s["rechazados"] > 0
    motivos = {r[0] for r in loaded["conn"].execute("SELECT DISTINCT motivo FROM rechazos_etl")}
    for expected in ("Nota fuera del rango 0-100", "Nota no numérica", "Asistencia de estudiante no registrado",
                     "La fecha no pertenece a ningún período académico", "Registro duplicado exacto",
                     "Campo requerido vacío: genero", "Documento de estudiante no registrado"):
        assert expected in motivos


def test_normalization_reached_database(loaded):
    c = loaded["conn"]
    assert c.execute("SELECT 1 FROM centros WHERE codigo='CE-005'").fetchone()        # '  ce-005 '
    assert c.execute("SELECT 1 FROM estudiantes WHERE codigo='E-0100'").fetchone()    # 'e-0100'
    assert c.execute("SELECT COUNT(*) FROM centros WHERE zona NOT IN ('urbana','rural')").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM regiones").fetchone()[0] == 16


def test_integrity_report_is_clean(loaded):
    rep = masters.integrity_report(loaded["conn"])
    assert (rep["registros"] == 0).all(), rep


def test_demo_student_indicators(loaded):
    r = loaded["conn"].execute("SELECT * FROM indicadores WHERE estudiante_codigo='E-0042' "
                               "AND periodo_codigo='2025-T3'").fetchone()
    assert (r["asistencia_pct"], r["promedio"], r["max_ausencias_consecutivas"]) == (72.0, 58.0, 3)
    assert r["nivel_alerta"] == "prioritario"


def test_alert_in_mongo_linked_to_sql(loaded):
    db, c = loaded["db"], loaded["conn"]
    al = db.alertas.find_one({"_id": "E-0042|2025-T3"})
    assert al and al["nivel"] == "prioritario" and al["estado"] == "abierta" and len(al["motivos"]) == 3
    sql_students = {r[0] for r in c.execute("SELECT codigo FROM estudiantes")}
    assert {a["estudiante_codigo"] for a in db.alertas.find()} <= sql_students     # F27
    n_sql = c.execute("SELECT COUNT(*) FROM indicadores WHERE nivel_alerta != 'regular'").fetchone()[0]
    assert db.alertas.count_documents({"vigente": True}) == n_sql


def test_imported_json_observations(loaded):
    db = loaded["db"]
    assert db.observaciones.find_one({"_id": "HIST-900", "estudiante_codigo": "E-0042"})
    assert db.observaciones.find_one({"_id": "HIST-901"}) is None


def test_rerun_is_idempotent(loaded):
    c, db = loaded["conn"], loaded["db"]
    before = sql.table_counts(c)
    alerts_before = db.alertas.count_documents({})
    again = pipeline.run(trigger="test", conn=c)
    assert again["aceptados"] == 0 and again["omitidos"] > 0          # archivos ya procesados se omiten
    forced = pipeline.run(trigger="test", force=True, conn=c)
    assert forced["aceptados"] > 0
    after = sql.table_counts(c)
    for t in ("estudiantes", "matriculas", "asistencias", "calificaciones", "recursos_tecnologicos", "indicadores"):
        assert before[t] == after[t], t
    assert db.alertas.count_documents({}) == alerts_before
    assert db.observaciones.count_documents({"origen": "importacion"}) == 31


def test_kpis_are_computed_from_data(loaded):
    c, db = loaded["conn"], loaded["db"]
    rules = sql.get_rules(c)
    k = kpi.compute(c, db, "2025-T3", rules)
    att = c.execute("SELECT 100.0*SUM(dias_asistidos)/SUM(dias_programados) FROM indicadores "
                    "WHERE periodo_codigo='2025-T3'").fetchone()[0]
    assert k["tasa_asistencia"]["valor"] == round(att, 1)
    prio = c.execute("SELECT COUNT(*) FROM indicadores WHERE periodo_codigo='2025-T3' "
                     "AND nivel_alerta='prioritario'").fetchone()[0]
    assert k["alertas_prioritarias"]["valor"] == prio
    assert k["alertas_sin_seguimiento"]["valor"] == db.alertas.count_documents({"periodo_codigo": "2025-T3",
                                                                                "vigente": True})
    assert 0 <= k["conectividad_escolar"]["valor"] <= 100
    filtered = kpi.compute(c, db, "2025-T3", rules, centros=["CE-021"])
    assert filtered["tasa_asistencia"]["denominador"] < k["tasa_asistencia"]["denominador"]


def test_quality_indicators(loaded):
    q = quality.by_source(loaded["conn"])
    assert set(q["fuente"]) >= {"asistencias", "calificaciones", "estudiantes"}
    assert (q["completitud_pct"] <= 100).all() and (q["consistencia_pct"] > 90).all()


def test_bad_file_does_not_stop_pipeline(fresh):
    from edualerta.etl import extract
    d = extract.incoming_dir("calificaciones")
    d.mkdir(parents=True, exist_ok=True)
    (d / "roto.csv").write_text("columna_x,columna_y\n1,2\n", encoding="utf-8")
    out = pipeline.run(trigger="test")
    assert out["estado"] == "con_advertencias"
    assert any("Faltan columnas requeridas" in e for e in out["errores"])
    assert all(p["estado"] == "ok" for p in out["pasos"])


def test_reject_reasons_match_quality_after_reprocessing(fresh):
    """Reprocesar no duplica los motivos de rechazo: coinciden con el total de la tabla de calidad."""
    c = fresh["conn"]
    pipeline.run(trigger="test", force=True, conn=c)
    assert int(quality.reject_reasons(c)["registros"].sum()) == int(quality.by_source(c)["rechazados"].sum())


def test_regional_level_filter_applies_to_technology(loaded):
    """F55: el filtro de nivel educativo también filtra conectividad y dispositivos."""
    from edualerta.services import regional, tech
    c = loaded["conn"]
    rules = sql.get_rules(c)
    periodo = sql.periods(c)[-1]
    _, nat = regional.region_table(c, periodo, rules, niveles_educativos=["media"])
    res = tech.resources_frame(c, periodo, rules)
    nivel = dict(c.execute("SELECT codigo, nivel FROM centros").fetchall())
    media = res[res["centro_codigo"].map(nivel) == "media"]
    assert nat["conectividad_pct"] == round(media["tiene_internet"].mean() * 100, 1)
