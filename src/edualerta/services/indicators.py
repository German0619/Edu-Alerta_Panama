"""Integración de fuentes y cálculo de indicadores por estudiante y período (F18, F19, F29-F32)."""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

from edualerta.db import sql
from edualerta.services.alerts import classify

KEY = ["estudiante_codigo", "periodo_codigo"]


def attendance_metrics(asis: pd.DataFrame) -> pd.DataFrame:
    """F29-F30. Las ausencias justificadas se excluyen de los días programados y cortan rachas."""
    cols = KEY + ["dias_registrados", "dias_programados", "dias_asistidos", "ausencias_injustificadas",
                  "ausencias_justificadas", "asistencia_pct", "max_ausencias_consecutivas", "episodios_ausencia"]
    if asis.empty:
        return pd.DataFrame(columns=cols)
    a = asis.sort_values(KEY + ["fecha"]).copy()
    a["asistio"] = a["estado"].isin(["presente", "tardanza"])
    a["aus"] = a["estado"].eq("ausente")
    a["jus"] = a["estado"].eq("justificada")
    g = a.groupby(KEY)
    out = pd.DataFrame({
        "dias_registrados": g.size(),
        "dias_asistidos": g["asistio"].sum(),
        "ausencias_injustificadas": g["aus"].sum(),
        "ausencias_justificadas": g["jus"].sum(),
    })
    out["dias_programados"] = out["dias_registrados"] - out["ausencias_justificadas"]
    out["asistencia_pct"] = (out["dias_asistidos"] / out["dias_programados"].where(out["dias_programados"] > 0) * 100
                             ).round(1)
    # rachas de ausencias consecutivas (días lectivos consecutivos registrados)
    a["run"] = (a["aus"] != g["aus"].shift()).cumsum()
    runs = a[a["aus"]].groupby(KEY + ["run"]).size().rename("largo").reset_index()
    rr = runs.groupby(KEY)["largo"].agg(max_ausencias_consecutivas="max", episodios_ausencia="count")
    out = out.join(rr).fillna({"max_ausencias_consecutivas": 0, "episodios_ausencia": 0}).reset_index()
    return out[cols]


def grade_metrics(cal: pd.DataFrame, nota_aprobacion: float) -> pd.DataFrame:
    """F31. Promedio simple de asignaturas por estudiante y período."""
    cols = KEY + ["promedio", "asignaturas_reprobadas", "aprobado"]
    if cal.empty:
        return pd.DataFrame(columns=cols)
    c = cal.copy()
    c["reprobada"] = c["nota"] < nota_aprobacion
    g = c.groupby(KEY)
    out = pd.DataFrame({"promedio": g["nota"].mean().round(1), "asignaturas_reprobadas": g["reprobada"].sum()})
    out["aprobado"] = (out["promedio"] >= nota_aprobacion).astype(int)
    return out.reset_index()[cols]


def compute_frame(conn: sqlite3.Connection, rules: dict) -> pd.DataFrame:
    mat = sql.query_df(conn, "SELECT estudiante_codigo, periodo_codigo, centro_codigo, grado FROM matriculas "
                             "WHERE estado='activa'")
    asis = sql.query_df(conn, "SELECT estudiante_codigo, periodo_codigo, fecha, estado FROM asistencias")
    cal = sql.query_df(conn, "SELECT estudiante_codigo, periodo_codigo, asignatura, nota FROM calificaciones")
    df = (mat.merge(attendance_metrics(asis), on=KEY, how="left")
             .merge(grade_metrics(cal, rules["alertas"]["nota_aprobacion"]), on=KEY, how="left"))
    df = df[(df["dias_registrados"].fillna(0) > 0) | df["promedio"].notna()].copy()
    for c in ("dias_programados", "dias_asistidos", "ausencias_injustificadas", "ausencias_justificadas",
              "max_ausencias_consecutivas", "episodios_ausencia", "asignaturas_reprobadas"):
        df[c] = df[c].fillna(0).astype(int)
    niveles, motivos = [], []
    for rec in df.to_dict("records"):
        nivel, mot = classify(rec, rules)
        niveles.append(nivel)
        motivos.append(json.dumps(mot, ensure_ascii=False))
    df["nivel_alerta"] = niveles
    df["motivos"] = motivos
    df["calculado_en"] = sql.now_iso()
    return df.drop(columns=["dias_registrados"])


def compute_all(conn: sqlite3.Connection, rules: dict) -> dict:
    df = compute_frame(conn, rules)
    conn.execute("DELETE FROM indicadores")
    cols = ["estudiante_codigo", "periodo_codigo", "centro_codigo", "grado", "dias_programados", "dias_asistidos",
            "ausencias_injustificadas", "ausencias_justificadas", "asistencia_pct", "max_ausencias_consecutivas",
            "episodios_ausencia", "promedio", "asignaturas_reprobadas", "aprobado", "nivel_alerta", "motivos",
            "calculado_en"]
    records = df[cols].astype(object).where(df[cols].notna(), None).to_dict("records")
    sql.upsert(conn, "indicadores", records, ["estudiante_codigo", "periodo_codigo"])
    conn.commit()
    return {"indicadores": len(df), **df["nivel_alerta"].value_counts().to_dict()}


def indicator_frame(conn: sqlite3.Connection, periodo: str | list | None = None, regiones=None, centros=None,
                    grados=None, zonas=None) -> pd.DataFrame:
    """Indicadores filtrados con contexto de centro y región (F05, F60)."""
    df = sql.query_df(conn, """
        SELECT i.*, c.nombre AS centro_nombre, c.region_codigo, r.nombre AS region_nombre, c.zona,
               c.dependencia, c.nivel AS nivel_educativo, p.anio, p.trimestre
        FROM indicadores i
        JOIN centros c ON c.codigo = i.centro_codigo
        JOIN regiones r ON r.codigo = c.region_codigo
        JOIN periodos p ON p.codigo = i.periodo_codigo""")
    if periodo:
        df = df[df["periodo_codigo"].isin([periodo] if isinstance(periodo, str) else periodo)]
    if regiones:
        df = df[df["region_codigo"].isin(regiones)]
    if centros:
        df = df[df["centro_codigo"].isin(centros)]
    if grados:
        df = df[df["grado"].isin(grados)]
    if zonas:
        df = df[df["zona"].isin(zonas)]
    return df.reset_index(drop=True)


def subject_averages(conn: sqlite3.Connection, periodo: str | None = None, centros=None) -> pd.DataFrame:
    """F31: promedio por asignatura y período."""
    df = sql.query_df(conn, """SELECT c.periodo_codigo, c.asignatura, m.centro_codigo, c.nota
                               FROM calificaciones c JOIN matriculas m
                                 ON m.estudiante_codigo=c.estudiante_codigo AND m.periodo_codigo=c.periodo_codigo""")
    if periodo:
        df = df[df["periodo_codigo"] == periodo]
    if centros:
        df = df[df["centro_codigo"].isin(centros)]
    return df.groupby(["periodo_codigo", "asignatura"], as_index=False)["nota"].mean().round(1)
