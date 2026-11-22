"""Recursos tecnológicos escolares (F45-F50)."""
from __future__ import annotations

import sqlite3

import pandas as pd

from edualerta.db import sql
from edualerta.services import audit

NECESIDAD_ORDEN = {"alta": 0, "media": 1, "baja": 2}


def classify_need(row: dict, rules: dict) -> tuple[str, list[str]]:
    """F48: criterios configurables y explícitos."""
    t = rules["tecnologia"]
    motivos, nivel = [], "baja"
    dpe = row.get("dispositivos_por_estudiante")
    if not row.get("tiene_internet"):
        motivos.append("Sin acceso a internet")
        nivel = "alta"
    elif row.get("velocidad_mbps", 0) < t["velocidad_minima_mbps"]:
        motivos.append(f"Internet deficiente ({row['velocidad_mbps']:.0f} Mbps < {t['velocidad_minima_mbps']})")
        nivel = "media"
    if dpe is not None and not pd.isna(dpe):
        if dpe < t["dispositivos_por_estudiante_critico"]:
            motivos.append(f"{dpe:.2f} dispositivos/estudiante (< {t['dispositivos_por_estudiante_critico']})")
            nivel = "alta"
        elif dpe < t["dispositivos_por_estudiante_minimo"]:
            motivos.append(f"{dpe:.2f} dispositivos/estudiante (< {t['dispositivos_por_estudiante_minimo']})")
            nivel = "media" if nivel == "baja" else nivel
    return nivel, motivos


def resources_frame(conn: sqlite3.Connection, periodo: str | None, rules: dict, regiones=None) -> pd.DataFrame:
    """F47: dispositivos funcionales / estudiantes matriculados, por centro."""
    df = sql.query_df(conn, """
        SELECT rt.*, c.nombre AS centro_nombre, c.region_codigo, r.nombre AS region_nombre, c.zona, c.dependencia,
               (SELECT COUNT(*) FROM matriculas m WHERE m.centro_codigo=rt.centro_codigo
                    AND m.periodo_codigo=rt.periodo_codigo AND m.estado='activa') AS matriculados
        FROM recursos_tecnologicos rt
        JOIN centros c ON c.codigo=rt.centro_codigo
        JOIN regiones r ON r.codigo=c.region_codigo""")
    if periodo:
        df = df[df["periodo_codigo"] == periodo]
    if regiones:
        df = df[df["region_codigo"].isin(regiones)]
    if df.empty:
        return df
    df = df.copy()
    df["dispositivos"] = df["computadoras_funcionales"] + df["tabletas_funcionales"]
    df["dispositivos_por_estudiante"] = (df["dispositivos"] / df["matriculados"].where(df["matriculados"] > 0)).round(2)
    res = [classify_need(r, rules) for r in df.to_dict("records")]
    df["necesidad"] = [r[0] for r in res]
    df["motivos"] = ["; ".join(r[1]) or "Sin carencias según criterios" for r in res]
    return df.reset_index(drop=True)


def priority_list(df: pd.DataFrame) -> pd.DataFrame:
    """F50: centros candidatos a atención tecnológica prioritaria."""
    if df.empty:
        return df
    out = df[df["necesidad"] != "baja"].copy()
    out["_o"] = out["necesidad"].map(NECESIDAD_ORDEN)
    out = out.sort_values(["_o", "tiene_internet", "dispositivos_por_estudiante", "matriculados"],
                          ascending=[True, True, True, False])
    out.insert(0, "prioridad", range(1, len(out) + 1))
    return out.drop(columns="_o").reset_index(drop=True)


def save_resources(conn: sqlite3.Connection, centro: str, periodo: str, tiene_internet: bool, velocidad: float,
                   computadoras: int, tabletas: int, usuario: str, perfil: str | None = None) -> None:
    """F45-F46: registro/actualización desde la interfaz."""
    if min(velocidad, computadoras, tabletas) < 0:
        raise ValueError("Los valores no pueden ser negativos.")
    velocidad = float(velocidad if tiene_internet else 0)  # sin internet no hay velocidad que registrar
    sql.upsert(conn, "recursos_tecnologicos", [{
        "centro_codigo": centro, "periodo_codigo": periodo, "tiene_internet": int(bool(tiene_internet)),
        "velocidad_mbps": velocidad, "computadoras_funcionales": int(computadoras),
        "tabletas_funcionales": int(tabletas), "actualizado_por": usuario, "actualizado_en": sql.now_iso()}],
        ["centro_codigo", "periodo_codigo"])
    conn.commit()
    audit.log(usuario, "actualizar_recursos", "recursos_tecnologicos", f"{centro}|{periodo}",
              {"internet": bool(tiene_internet), "velocidad": velocidad, "computadoras": computadoras,
               "tabletas": tabletas}, perfil)
