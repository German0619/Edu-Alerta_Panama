"""Comparación regional (F51-F56)."""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

from edualerta.etl.pipeline import processed_geojson_path
from edualerta.services import indicators, tech

MUESTRA_MINIMA = 30


def geojson() -> dict | None:
    path = processed_geojson_path()
    return json.loads(path.read_text("utf-8")) if path.exists() else None


def _aggregate(ind: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = ind.groupby(by)
    out = pd.DataFrame({
        "estudiantes": g["estudiante_codigo"].nunique(),
        "centros": g["centro_codigo"].nunique(),
        "dias_asistidos": g["dias_asistidos"].sum(),
        "dias_programados": g["dias_programados"].sum(),
        "promedio": g["promedio"].mean().round(1),
        "aprobados": g["aprobado"].sum(),
        "evaluados": g["aprobado"].count(),
        "prioritarios": g["nivel_alerta"].apply(lambda s: (s == "prioritario").sum()),
    })
    out["asistencia_pct"] = (out["dias_asistidos"] / out["dias_programados"] * 100).round(1)
    out["aprobacion_pct"] = (out["aprobados"] / out["evaluados"] * 100).round(1)
    out["prioritarios_pct"] = (out["prioritarios"] / out["estudiantes"] * 100).round(1)
    return out.reset_index()


def region_table(conn: sqlite3.Connection, periodo: str, rules: dict, zonas=None, centros=None,
                 niveles_educativos=None) -> tuple[pd.DataFrame, dict]:
    """F52-F55: indicadores agregados por región + referencia nacional."""
    ind = indicators.indicator_frame(conn, periodo, centros=centros, zonas=zonas)
    if niveles_educativos:
        ind = ind[ind["nivel_educativo"].isin(niveles_educativos)]
    if ind.empty:
        return pd.DataFrame(), {}
    reg = _aggregate(ind, ["region_codigo", "region_nombre"])
    res = tech.resources_frame(conn, periodo, rules)
    if centros:
        res = res[res["centro_codigo"].isin(centros)] if not res.empty else res
    if zonas and not res.empty:
        res = res[res["zona"].isin(zonas)]
    if niveles_educativos and not res.empty:  # el filtro de nivel también aplica a conectividad y dispositivos
        nivel = dict(conn.execute("SELECT codigo, nivel FROM centros").fetchall())
        res = res[res["centro_codigo"].map(nivel).isin(niveles_educativos)]
    if not res.empty:
        t = res.groupby("region_codigo").agg(centros_internet=("tiene_internet", "sum"),
                                              centros_evaluados=("tiene_internet", "count"),
                                              dispositivos=("dispositivos", "sum"),
                                              matriculados=("matriculados", "sum")).reset_index()
        t["conectividad_pct"] = (t["centros_internet"] / t["centros_evaluados"] * 100).round(1)
        t["dispositivos_por_estudiante"] = (t["dispositivos"] / t["matriculados"]).round(2)
        reg = reg.merge(t[["region_codigo", "conectividad_pct", "dispositivos_por_estudiante"]], on="region_codigo",
                        how="left")
    nat = {
        "asistencia_pct": round(ind["dias_asistidos"].sum() / ind["dias_programados"].sum() * 100, 1),
        "aprobacion_pct": round(ind["aprobado"].sum() / ind["aprobado"].count() * 100, 1),
        "promedio": round(ind["promedio"].mean(), 1),
        "conectividad_pct": round(res["tiene_internet"].mean() * 100, 1) if not res.empty else None,
        "dispositivos_por_estudiante": round(res["dispositivos"].sum() / res["matriculados"].sum(), 2)
        if not res.empty else None,
        "estudiantes": int(ind["estudiante_codigo"].nunique()),
    }
    flags = [unfavorable_flags(r, nat, rules) for r in reg.to_dict("records")]
    reg["alertas_regionales"] = ["; ".join(f) for f in flags]
    reg["n_criterios_desfavorables"] = [len(f) for f in flags]
    reg["muestra_suficiente"] = reg["estudiantes"] >= MUESTRA_MINIMA
    return reg, nat


def unfavorable_flags(r: dict, nat: dict, rules: dict) -> list[str]:
    """F56: criterios transparentes frente a la referencia nacional de la muestra."""
    brecha = rules["recomendaciones"]["brecha_asistencia_region"]
    t = rules["tecnologia"]
    flags = []
    if r["asistencia_pct"] < nat["asistencia_pct"] - brecha:
        flags.append(f"Asistencia {r['asistencia_pct']} % < nacional {nat['asistencia_pct']} % − {brecha}")
    if r["aprobacion_pct"] < nat["aprobacion_pct"] - 10:
        flags.append(f"Aprobación {r['aprobacion_pct']} % < nacional {nat['aprobacion_pct']} % − 10")
    if pd.notna(r.get("conectividad_pct")) and r["conectividad_pct"] < 50:
        flags.append(f"Conectividad {r['conectividad_pct']} % < 50 %")
    if pd.notna(r.get("dispositivos_por_estudiante")) and r["dispositivos_por_estudiante"] < t[
            "dispositivos_por_estudiante_minimo"]:
        flags.append(f"{r['dispositivos_por_estudiante']} disp./est. < {t['dispositivos_por_estudiante_minimo']}")
    return flags


def region_trend(conn: sqlite3.Connection, region: str) -> pd.DataFrame:
    ind = indicators.indicator_frame(conn, regiones=[region])
    if ind.empty:
        return ind
    out = _aggregate(ind, ["periodo_codigo", "anio", "trimestre"]).sort_values(["anio", "trimestre"])
    return out
