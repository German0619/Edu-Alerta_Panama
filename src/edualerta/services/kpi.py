"""Cálculo de KPI gerenciales desde los datos (F57-F63). Ningún valor se escribe a mano."""
from __future__ import annotations

import sqlite3

import pandas as pd
from pymongo.database import Database
from pymongo.errors import PyMongoError

from edualerta import config
from edualerta.db import sql
from edualerta.services import indicators, tech


def _pct(num, den):
    return round(num / den * 100, 1) if den else None


def compute(conn: sqlite3.Connection, db: Database | None, periodo: str, rules: dict, regiones=None, centros=None,
            grados=None) -> dict:
    catalog = config.kpi_catalog()
    ind = indicators.indicator_frame(conn, periodo, regiones=regiones, centros=centros, grados=grados)
    scope_centros = sorted(ind["centro_codigo"].unique()) if not ind.empty else []
    res = tech.resources_frame(conn, periodo, rules, regiones=regiones)
    if centros and not res.empty:
        res = res[res["centro_codigo"].isin(centros)]
    if grados and not res.empty:  # cada centro es de un solo nivel: el filtro de grado acota también los recursos
        res = res[res["centro_codigo"].isin(scope_centros)]

    values: dict[str, dict] = {}
    values["tasa_asistencia"] = {"valor": _pct(ind["dias_asistidos"].sum(), ind["dias_programados"].sum()),
                                 "numerador": int(ind["dias_asistidos"].sum()),
                                 "denominador": int(ind["dias_programados"].sum())}
    ev = ind["aprobado"].dropna()
    values["tasa_aprobacion"] = {"valor": _pct(ev.sum(), len(ev)), "numerador": int(ev.sum()),
                                 "denominador": int(len(ev))}
    values["conectividad_escolar"] = {
        "valor": _pct(res["tiene_internet"].sum(), len(res)) if not res.empty else None,
        "numerador": int(res["tiene_internet"].sum()) if not res.empty else 0, "denominador": len(res)}
    disp = int(res["dispositivos"].sum()) if not res.empty else 0
    mat = int(res["matriculados"].sum()) if not res.empty else 0
    values["disponibilidad_dispositivos"] = {"valor": round(disp / mat, 2) if mat else None,
                                             "numerador": disp, "denominador": mat}

    alert_q = {"periodo_codigo": periodo, "vigente": True, "estado": {"$ne": "descartada"}}
    if scope_centros or centros or regiones:
        alert_q["centro_codigo"] = {"$in": list(scope_centros)}
    if grados:
        alert_q["grado"] = {"$in": [int(g) for g in grados]}
    mongo_ok = db is not None
    try:
        if not mongo_ok:
            raise PyMongoError("sin conexión")
        alerts = list(db.alertas.find(alert_q, {"nivel": 1, "caso_id": 1}))
        case_ids = [a["caso_id"] for a in alerts if a.get("caso_id")]
        cases = {c["_id"]: c for c in db.casos.find({"_id": {"$in": case_ids}}, {"n_intervenciones": 1})}
        prio = sum(1 for a in alerts if a["nivel"] == "prioritario")
        with_action = sum(1 for c in cases.values() if c.get("n_intervenciones", 0) > 0)
        sin_seg = sum(1 for a in alerts if not a.get("caso_id") or cases.get(a["caso_id"], {}).get(
            "n_intervenciones", 0) == 0)
        values["alertas_prioritarias"] = {"valor": prio, "numerador": prio, "denominador": len(alerts)}
        values["intervenciones_realizadas"] = {"valor": _pct(with_action, len(cases)), "numerador": with_action,
                                               "denominador": len(cases)}
        values["alertas_sin_seguimiento"] = {"valor": sin_seg, "numerador": sin_seg, "denominador": len(alerts)}
    except PyMongoError:
        for k in ("alertas_prioritarias", "intervenciones_realizadas", "alertas_sin_seguimiento"):
            values[k] = {"valor": None, "numerador": None, "denominador": None, "error": "MongoDB no disponible"}

    return {k: {**catalog[k], **values[k]} for k in catalog}


def trend(conn: sqlite3.Connection, rules: dict, regiones=None, centros=None, grados=None) -> pd.DataFrame:
    """F58: evolución histórica por período (asistencia, aprobación, promedio y % prioritarios)."""
    ind = indicators.indicator_frame(conn, regiones=regiones, centros=centros, grados=grados)
    if ind.empty:
        return pd.DataFrame()
    g = ind.groupby(["periodo_codigo", "anio", "trimestre"])
    out = pd.DataFrame({
        "asistencia_pct": g["dias_asistidos"].sum() / g["dias_programados"].sum() * 100,
        "aprobacion_pct": g["aprobado"].mean() * 100,
        "promedio": g["promedio"].mean(),
        "prioritarios": g["nivel_alerta"].apply(lambda s: (s == "prioritario").sum()),
        "preventivos": g["nivel_alerta"].apply(lambda s: (s == "preventivo").sum()),
        "estudiantes": g["estudiante_codigo"].nunique(),
    }).round(1).reset_index().sort_values(["anio", "trimestre"])
    rec = sql.query_df(conn, "SELECT periodo_codigo, centro_codigo, tiene_internet FROM recursos_tecnologicos")
    rec = rec[rec["centro_codigo"].isin(ind["centro_codigo"].unique())]  # mismos filtros que los indicadores
    res = (rec.groupby("periodo_codigo")["tiene_internet"].mean() * 100).rename("conectividad_pct").reset_index()
    return out.merge(res.round(1), on="periodo_codigo", how="left")


def alert_distribution(conn: sqlite3.Connection, periodo: str, regiones=None, centros=None,
                       grados=None) -> pd.DataFrame:
    """F59: distribución por nivel y centro."""
    ind = indicators.indicator_frame(conn, periodo, regiones=regiones, centros=centros, grados=grados)
    if ind.empty:
        return ind
    return (ind.groupby(["centro_codigo", "centro_nombre", "region_nombre", "nivel_alerta"]).size()
               .rename("estudiantes").reset_index())
