"""Gestión de centros, estudiantes, períodos y matrículas (F01-F06)."""
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

from edualerta.db import sql
from edualerta.etl import transform
from edualerta.services import audit


def _validated(entity: str, record: dict, conn: sqlite3.Connection) -> dict:
    """Reutiliza exactamente las mismas reglas del ETL para los formularios."""
    batch = transform.Batch(pd.DataFrame([{k: (None if v is None else str(v)) for k, v in record.items()}]),
                            entity, "formulario")
    rows = transform.CLEANERS[entity](batch, transform.RefData.load(conn))
    if batch.rejects:
        raise ValueError(batch.rejects[0]["motivo"])
    return rows[0]


def save(conn: sqlite3.Connection, entity: str, record: dict, usuario: str, perfil: str | None = None,
         allow_update: bool = False) -> dict:
    row = _validated(entity, record, conn)
    keys = transform.CONFLICT_KEYS[entity]
    where = " AND ".join(f"{k}=?" for k in keys)
    exists = conn.execute(f"SELECT 1 FROM {entity} WHERE {where}", tuple(row[k] for k in keys)).fetchone()
    if exists and not allow_update:
        raise ValueError(f"Ya existe un registro con {', '.join(f'{k}={row[k]}' for k in keys)} (F06).")
    sql.upsert(conn, entity, [row], keys)
    conn.commit()
    audit.log(usuario, f"{'actualizar' if exists else 'registrar'}_{entity}", entity,
              "|".join(str(row[k]) for k in keys), row, perfil)
    return row


def next_student_code(conn: sqlite3.Connection) -> str:
    last = conn.execute("SELECT MAX(CAST(SUBSTR(codigo, 3) AS INTEGER)) FROM estudiantes").fetchone()[0] or 0
    return f"E-{last + 1:04d}"


def next_center_code(conn: sqlite3.Connection) -> str:
    last = conn.execute("SELECT MAX(CAST(SUBSTR(codigo, 4) AS INTEGER)) FROM centros").fetchone()[0] or 0
    return f"CE-{last + 1:03d}"


def students_frame(conn: sqlite3.Connection, periodo=None, regiones=None, centros=None, grados=None) -> pd.DataFrame:
    """F04-F05: estudiantes con su matrícula, centro y región."""
    df = sql.query_df(conn, """
        SELECT e.codigo, e.genero, e.anio_nacimiento, m.periodo_codigo, m.grado, m.estado AS estado_matricula,
               m.centro_codigo, c.nombre AS centro, c.region_codigo, r.nombre AS region, c.zona
        FROM estudiantes e
        LEFT JOIN matriculas m ON m.estudiante_codigo = e.codigo
        LEFT JOIN centros c ON c.codigo = m.centro_codigo
        LEFT JOIN regiones r ON r.codigo = c.region_codigo""")
    if periodo:
        df = df[df["periodo_codigo"] == periodo]
    if regiones:
        df = df[df["region_codigo"].isin(regiones)]
    if centros:
        df = df[df["centro_codigo"].isin(centros)]
    if grados:
        df = df[df["grado"].isin(grados)]
    return df.reset_index(drop=True)


def centers_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    return sql.query_df(conn, """SELECT c.*, r.nombre AS region_nombre,
            (SELECT COUNT(DISTINCT estudiante_codigo) FROM matriculas m WHERE m.centro_codigo=c.codigo) AS estudiantes
        FROM centros c JOIN regiones r ON r.codigo=c.region_codigo ORDER BY c.codigo""")


def integrity_report(conn: sqlite3.Connection) -> pd.DataFrame:
    """F06: verificación de duplicados y relaciones huérfanas."""
    checks = {
        "Estudiantes sin matrícula": "SELECT COUNT(*) FROM estudiantes e WHERE NOT EXISTS "
                                     "(SELECT 1 FROM matriculas m WHERE m.estudiante_codigo=e.codigo)",
        "Matrículas con centro inexistente": "SELECT COUNT(*) FROM matriculas m LEFT JOIN centros c "
                                             "ON c.codigo=m.centro_codigo WHERE c.codigo IS NULL",
        "Matrículas con estudiante inexistente": "SELECT COUNT(*) FROM matriculas m LEFT JOIN estudiantes e "
                                                 "ON e.codigo=m.estudiante_codigo WHERE e.codigo IS NULL",
        "Estudiantes con más de un centro en el mismo período":
            "SELECT COUNT(*) FROM (SELECT estudiante_codigo, periodo_codigo FROM matriculas "
            "GROUP BY 1,2 HAVING COUNT(DISTINCT centro_codigo) > 1)",
        "Asistencias sin matrícula en su período":
            "SELECT COUNT(*) FROM asistencias a WHERE NOT EXISTS (SELECT 1 FROM matriculas m WHERE "
            "m.estudiante_codigo=a.estudiante_codigo AND m.periodo_codigo=a.periodo_codigo)",
        "Calificaciones sin matrícula en su período":
            "SELECT COUNT(*) FROM calificaciones a WHERE NOT EXISTS (SELECT 1 FROM matriculas m WHERE "
            "m.estudiante_codigo=a.estudiante_codigo AND m.periodo_codigo=a.periodo_codigo)",
        "Centros sin estudiantes": "SELECT COUNT(*) FROM centros c WHERE NOT EXISTS "
                                   "(SELECT 1 FROM matriculas m WHERE m.centro_codigo=c.codigo)",
        "Claves foráneas rotas (PRAGMA foreign_key_check)": "SELECT COUNT(*) FROM pragma_foreign_key_check",
    }
    rows = []
    for name, q in checks.items():
        n = conn.execute(q).fetchone()[0]
        rows.append({"verificación": name, "registros": n, "resultado": "OK" if n == 0 else "Revisar"})
    return pd.DataFrame(rows)


def default_period_dates(anio: int, trimestre: int) -> tuple[date, date]:
    starts = {1: (3, 1), 2: (6, 15), 3: (9, 20)}
    ends = {1: (6, 6), 2: (9, 12), 3: (12, 12)}
    return date(anio, *starts[trimestre]), date(anio, *ends[trimestre])
