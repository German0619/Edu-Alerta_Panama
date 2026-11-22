"""Pruebas de limpieza, normalización y reglas de negocio del ETL (F15-F17, F83)."""
import pandas as pd

from edualerta.etl import extract, transform


def ref(**kw):
    per = pd.DataFrame({"codigo": ["2025-T1"], "fecha_inicio": [pd.Timestamp("2025-03-03")],
                        "fecha_fin": [pd.Timestamp("2025-06-06")]})
    base = dict(regiones={"PCE"}, centros={"CE-001"}, estudiantes={"E-0001", "E-0002"}, periodos=per,
                matriculas={"E-0001|2025-T1", "E-0002|2025-T1"})
    base.update(kw)
    return transform.RefData(**base)


def test_normalize_columns_accents_and_alias():
    df = pd.DataFrame(columns=["Código Estudiante", " Calificación ", "Materia", "Periodo"])
    out = extract.normalize_columns(df, {"codigo_estudiante": "estudiante_codigo", "calificacion": "nota",
                                         "materia": "asignatura", "periodo": "periodo_codigo"})
    assert list(out.columns) == ["estudiante_codigo", "nota", "asignatura", "periodo_codigo"]


def test_student_and_center_codes_are_normalized():
    s = transform.norm_student(pd.Series(["e42", " E-0042 ", "E_42", "X-1", None]))
    assert s.tolist()[:3] == ["E-0042"] * 3 and s.iloc[3] is None
    c = transform.norm_center(pd.Series(["  ce-005 ", "CE5", "C-5"]))
    assert c.tolist()[:2] == ["CE-005", "CE-005"] and c.iloc[2] is None


def test_mixed_date_formats():
    d = transform.parse_dates(pd.Series(["2025-03-10", "10/03/2025", "10-03-2025", "2025-13-45", None]))
    assert d.iloc[0] == d.iloc[1] == d.iloc[2] == pd.Timestamp("2025-03-10")
    assert pd.isna(d.iloc[3]) and pd.isna(d.iloc[4])


def test_grades_business_rules():
    df = pd.DataFrame({"estudiante_codigo": ["E-0001", "E-0001", "E-0001", "E-0002", "E-9999", "E-0002"],
                       "periodo_codigo": ["2025-T1"] * 6,
                       "asignatura": ["Español", "Inglés", "Arte", "Español", "Español", "Español"],
                       "nota": ["85", "105", "8O", "", "70", "71"]})
    b = transform.Batch(df, "calificaciones", "t.csv")
    rows = transform.clean_calificaciones(b, ref())
    motivos = {r["motivo"] for r in b.rejects}
    assert "Nota fuera del rango 0-100" in motivos
    assert "Nota no numérica" in motivos
    assert "Campo requerido vacío: nota" in motivos
    assert "Calificación de estudiante no registrado" in motivos
    assert {(r["estudiante_codigo"], r["asignatura"], r["nota"]) for r in rows} == {
        ("E-0001", "Español", 85.0), ("E-0002", "Español", 71.0)}


def test_attendance_rules_and_period_assignment():
    df = pd.DataFrame({"estudiante_codigo": ["E-0001", "e1", "E-0002", "E-9999", "E-0001", "E-0002"],
                       "fecha": ["2025-03-04", "05/03/2025", "2025-06-10", "2025-03-04", "2025-03-06", "2025-03-07"],
                       "estado": ["P", "Ausente", "presente", "presente", "dormido", "J"]})
    b = transform.Batch(df, "asistencias", "a.csv")
    rows = transform.clean_asistencias(b, ref())
    motivos = [r["motivo"] for r in b.rejects]
    assert "La fecha no pertenece a ningún período académico" in motivos
    assert "Asistencia de estudiante no registrado" in motivos
    assert "Estado de asistencia no reconocido" in motivos
    assert [(r["estudiante_codigo"], r["fecha"], r["estado"], r["periodo_codigo"]) for r in rows] == [
        ("E-0001", "2025-03-04", "presente", "2025-T1"), ("E-0001", "2025-03-05", "ausente", "2025-T1"),
        ("E-0002", "2025-03-07", "justificada", "2025-T1")]


def test_exact_duplicates_are_rejected_once():
    df = pd.DataFrame({"codigo": ["E-0001", "E-0001", "E-0003"], "genero": ["F", "F", "M"],
                       "anio_nacimiento": ["2011", "2011", "2010"]})
    b = transform.Batch(df, "estudiantes", "e.csv")
    rows = transform.clean_estudiantes(b, ref())
    assert len(rows) == 2 and [r["motivo"] for r in b.rejects] == ["Registro duplicado exacto"]


def test_preview_flags_missing_columns():
    src = {"formato": "csv", "requeridas": ["estudiante_codigo", "fecha", "estado"],
           "alias": {"codigo_estudiante": "estudiante_codigo"}}
    pv = extract.preview(b"codigo_estudiante,fecha\nE-0001,2025-03-04\n", src)
    assert pv["faltantes"] == ["estado"] and not pv["valido"] and pv["registros"] == 1


def test_invalid_json_raises_source_error():
    import pytest
    with pytest.raises(extract.SourceError):
        extract.preview(b"{no es json", {"formato": "json", "requeridas": []})


def test_observations_optional_author_role_is_filled():
    """Un JSON donde solo algunos documentos traen autor_rol no debe guardar NaN en MongoDB."""
    df = pd.DataFrame([
        {"id": "A", "estudiante_codigo": "E-0001", "fecha": "2025-03-10", "tipo": "Diagnostico", "texto": "x"},
        {"id": "B", "estudiante_codigo": "E-0002", "fecha": "2025-03-11", "tipo": "intervencion", "texto": "y",
         "autor_rol": "orientador"},
    ])
    recs = transform.clean_observaciones(transform.Batch(df, "seguimiento_historico", "s.json"), ref())
    assert [r["autor_rol"] for r in recs] == ["docente", "orientador"]
    assert recs[0]["tipo"] == "diagnostico"
