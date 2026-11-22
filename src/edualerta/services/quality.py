"""Indicadores de calidad de datos (F77) y aptitud de la información para decidir (F78 · R1)."""
from __future__ import annotations

import sqlite3

import pandas as pd

from edualerta.db import sql

UMBRAL_APTO = 95.0


def by_source(conn: sqlite3.Connection) -> pd.DataFrame:
    files = sql.query_df(conn, "SELECT fuente, SUM(registros) AS leidos, SUM(aceptados) AS aceptados, "
                               "SUM(rechazados) AS rechazados, COUNT(*) AS archivos "
                               "FROM archivos_procesados GROUP BY fuente")
    if files.empty:
        return files
    rej = sql.query_df(conn, """SELECT r.fuente AS fuente,
            SUM(CASE WHEN motivo LIKE 'Campo requerido vacío%' THEN 1 ELSE 0 END) AS incompletos,
            SUM(CASE WHEN motivo LIKE 'Registro duplicado%' OR motivo LIKE 'Clave repetida%' THEN 1 ELSE 0 END)
                AS duplicados
        FROM rechazos_etl r
        JOIN archivos_procesados a
          ON a.ejecucion_id = r.ejecucion_id AND a.archivo = r.archivo AND a.fuente = r.fuente
        GROUP BY r.fuente""")
    df = files.merge(rej, on="fuente", how="left").fillna(0)
    df["inconsistentes"] = df["rechazados"] - df["incompletos"] - df["duplicados"]
    df["completitud_pct"] = ((1 - df["incompletos"] / df["leidos"]) * 100).round(2)
    df["consistencia_pct"] = ((1 - df["inconsistentes"] / df["leidos"]) * 100).round(2)
    df["aceptacion_pct"] = (df["aceptados"] / df["leidos"] * 100).round(2)
    df["apto_para_decidir"] = (df["completitud_pct"] >= UMBRAL_APTO) & (df["consistencia_pct"] >= UMBRAL_APTO)
    return df


def rejects(conn: sqlite3.Connection, limit: int = 1000) -> pd.DataFrame:
    return sql.query_df(conn, "SELECT r.ejecucion_id, r.fuente, r.archivo, r.fila, r.motivo, r.datos "
                              "FROM rechazos_etl r ORDER BY r.id DESC LIMIT ?", (limit,))


def reject_reasons(conn: sqlite3.Connection) -> pd.DataFrame:
    """Motivos de rechazo de la versión vigente de cada archivo (mismo criterio que `by_source`).

    Reprocesar un archivo vuelve a registrar sus rechazos en una nueva ejecución; sumar el historial completo
    contaría dos veces el mismo registro defectuoso.
    """
    return sql.query_df(conn, """SELECT r.fuente, r.motivo, COUNT(*) AS registros
        FROM rechazos_etl r
        JOIN archivos_procesados a
          ON a.ejecucion_id = r.ejecucion_id AND a.archivo = r.archivo AND a.fuente = r.fuente
        GROUP BY r.fuente, r.motivo ORDER BY registros DESC""")


def coverage(conn: sqlite3.Connection) -> pd.DataFrame:
    """Cobertura: matriculados con indicadores calculados por período."""
    return sql.query_df(conn, """
        SELECT m.periodo_codigo, COUNT(*) AS matriculados,
               SUM(CASE WHEN i.estudiante_codigo IS NOT NULL THEN 1 ELSE 0 END) AS con_indicadores,
               ROUND(100.0 * SUM(CASE WHEN i.estudiante_codigo IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1)
                   AS cobertura_pct
        FROM matriculas m
        LEFT JOIN indicadores i ON i.estudiante_codigo=m.estudiante_codigo AND i.periodo_codigo=m.periodo_codigo
        JOIN periodos p ON p.codigo=m.periodo_codigo
        GROUP BY m.periodo_codigo ORDER BY p.anio, p.trimestre""")
