"""Pruebas de cálculos de indicadores, clasificación de alertas y criterios (F29-F33, F48, F70, F83)."""
import pandas as pd

from edualerta import config
from edualerta.services import indicators, recommendations, tech
from edualerta.services.alerts import classify


def rules():
    s = config.settings()
    return {k: s[k] for k in config.EDITABLE_SECTIONS}


def test_attendance_metrics_runs_and_justified():
    estados = ["presente", "ausente", "ausente", "justificada", "ausente", "ausente", "ausente", "tardanza",
               "presente", "ausente"]
    df = pd.DataFrame({"estudiante_codigo": "E-0001", "periodo_codigo": "2025-T1",
                       "fecha": pd.date_range("2025-03-03", periods=10).strftime("%Y-%m-%d"), "estado": estados})
    m = indicators.attendance_metrics(df).iloc[0]
    assert m["dias_programados"] == 9            # justificada excluida
    assert m["dias_asistidos"] == 3              # presente + tardanza
    assert m["asistencia_pct"] == round(3 / 9 * 100, 1)
    assert m["max_ausencias_consecutivas"] == 3  # la justificada corta la racha
    assert m["episodios_ausencia"] == 3


def test_grade_metrics():
    df = pd.DataFrame({"estudiante_codigo": "E-0001", "periodo_codigo": "2025-T1",
                       "asignatura": list("ABCDEF"), "nota": [52, 55, 60, 62, 57, 62]})
    g = indicators.grade_metrics(df, 61).iloc[0]
    assert g["promedio"] == 58.0 and g["asignaturas_reprobadas"] == 4 and g["aprobado"] == 0


def test_demo_case_e0042_is_priority_with_three_reasons():
    nivel, motivos = classify({"asistencia_pct": 72.0, "promedio": 58.0, "max_ausencias_consecutivas": 3}, rules())
    assert nivel == "prioritario"
    assert {m["criterio"] for m in motivos} == {"asistencia", "promedio", "ausencias_consecutivas"}
    assert all(m["nivel"] == "prioritario" for m in motivos)
    assert "72.0 %" in motivos[0]["texto"]


def test_preventive_and_regular():
    nivel, motivos = classify({"asistencia_pct": 88.0, "promedio": 75.0, "max_ausencias_consecutivas": 1}, rules())
    assert nivel == "preventivo" and len(motivos) == 1 and motivos[0]["criterio"] == "asistencia"
    assert classify({"asistencia_pct": 96.0, "promedio": 80.0, "max_ausencias_consecutivas": 0}, rules()) == (
        "regular", [])


def test_missing_values_do_not_trigger():
    nivel, _ = classify({"asistencia_pct": None, "promedio": float("nan"), "max_ausencias_consecutivas": 0}, rules())
    assert nivel == "regular"


def test_thresholds_are_configurable():
    r = rules()
    r["alertas"]["prioritario"]["asistencia_min"] = 70
    nivel, _ = classify({"asistencia_pct": 72.0, "promedio": 80.0, "max_ausencias_consecutivas": 0}, r)
    assert nivel == "preventivo"


def test_tech_need_classification():
    r = rules()
    assert tech.classify_need({"tiene_internet": 0, "velocidad_mbps": 0, "dispositivos_por_estudiante": 0.5}, r)[0] == "alta"
    assert tech.classify_need({"tiene_internet": 1, "velocidad_mbps": 50, "dispositivos_por_estudiante": 0.05}, r)[0] == "alta"
    assert tech.classify_need({"tiene_internet": 1, "velocidad_mbps": 5, "dispositivos_por_estudiante": 0.5}, r)[0] == "media"
    assert tech.classify_need({"tiene_internet": 1, "velocidad_mbps": 50, "dispositivos_por_estudiante": 0.2}, r)[0] == "media"
    assert tech.classify_need({"tiene_internet": 1, "velocidad_mbps": 50, "dispositivos_por_estudiante": 0.6}, r) == (
        "baja", [])


def test_risk_level():
    assert recommendations.risk_level(1, 5) == "bajo"
    assert recommendations.risk_level(2, 4) == "medio"
    assert recommendations.risk_level(3, 5) == "alto"
