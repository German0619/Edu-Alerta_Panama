"""Persistencia relacional SQLite (F23, F24): esquema, conexión y utilidades."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from edualerta import config

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS regiones (
    codigo      TEXT PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,
    tipo        TEXT NOT NULL DEFAULT 'provincial' CHECK (tipo IN ('provincial','comarcal','metropolitana'))
);

CREATE TABLE IF NOT EXISTS centros (
    codigo          TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    region_codigo   TEXT NOT NULL REFERENCES regiones(codigo),
    zona            TEXT NOT NULL CHECK (zona IN ('urbana','rural')),
    dependencia     TEXT NOT NULL CHECK (dependencia IN ('oficial','particular')),
    nivel           TEXT NOT NULL DEFAULT 'premedia' CHECK (nivel IN ('primaria','premedia','media'))
);

CREATE TABLE IF NOT EXISTS periodos (
    codigo          TEXT PRIMARY KEY,
    anio            INTEGER NOT NULL CHECK (anio BETWEEN 2000 AND 2100),
    trimestre       INTEGER NOT NULL CHECK (trimestre BETWEEN 1 AND 3),
    fecha_inicio    TEXT NOT NULL,
    fecha_fin       TEXT NOT NULL,
    UNIQUE (anio, trimestre),
    CHECK (fecha_inicio < fecha_fin)
);

CREATE TABLE IF NOT EXISTS estudiantes (
    codigo          TEXT PRIMARY KEY CHECK (codigo GLOB 'E-[0-9][0-9][0-9][0-9]'),
    genero          TEXT NOT NULL CHECK (genero IN ('F','M')),
    anio_nacimiento INTEGER NOT NULL CHECK (anio_nacimiento BETWEEN 1990 AND 2025),
    sintetico       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS matriculas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_codigo   TEXT NOT NULL REFERENCES estudiantes(codigo),
    centro_codigo       TEXT NOT NULL REFERENCES centros(codigo),
    periodo_codigo      TEXT NOT NULL REFERENCES periodos(codigo),
    grado               INTEGER NOT NULL CHECK (grado BETWEEN 1 AND 12),
    estado              TEXT NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa','retirada','trasladada')),
    UNIQUE (estudiante_codigo, periodo_codigo)
);

CREATE TABLE IF NOT EXISTS asistencias (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_codigo   TEXT NOT NULL REFERENCES estudiantes(codigo),
    periodo_codigo      TEXT NOT NULL REFERENCES periodos(codigo),
    fecha               TEXT NOT NULL,
    estado              TEXT NOT NULL CHECK (estado IN ('presente','ausente','justificada','tardanza')),
    UNIQUE (estudiante_codigo, fecha)
);
CREATE INDEX IF NOT EXISTS ix_asist_est_per ON asistencias(estudiante_codigo, periodo_codigo);

CREATE TABLE IF NOT EXISTS calificaciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_codigo   TEXT NOT NULL REFERENCES estudiantes(codigo),
    periodo_codigo      TEXT NOT NULL REFERENCES periodos(codigo),
    asignatura          TEXT NOT NULL,
    nota                REAL NOT NULL CHECK (nota BETWEEN 0 AND 100),
    UNIQUE (estudiante_codigo, periodo_codigo, asignatura)
);

CREATE TABLE IF NOT EXISTS recursos_tecnologicos (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    centro_codigo               TEXT NOT NULL REFERENCES centros(codigo),
    periodo_codigo              TEXT NOT NULL REFERENCES periodos(codigo),
    tiene_internet              INTEGER NOT NULL CHECK (tiene_internet IN (0,1)),
    velocidad_mbps              REAL NOT NULL DEFAULT 0 CHECK (velocidad_mbps >= 0),
    computadoras_funcionales    INTEGER NOT NULL CHECK (computadoras_funcionales >= 0),
    tabletas_funcionales        INTEGER NOT NULL CHECK (tabletas_funcionales >= 0),
    actualizado_por             TEXT,
    actualizado_en              TEXT,
    UNIQUE (centro_codigo, periodo_codigo)
);

CREATE TABLE IF NOT EXISTS indicadores (
    estudiante_codigo           TEXT NOT NULL REFERENCES estudiantes(codigo),
    periodo_codigo              TEXT NOT NULL REFERENCES periodos(codigo),
    centro_codigo               TEXT NOT NULL REFERENCES centros(codigo),
    grado                       INTEGER NOT NULL,
    dias_programados            INTEGER NOT NULL,
    dias_asistidos              INTEGER NOT NULL,
    ausencias_injustificadas    INTEGER NOT NULL,
    ausencias_justificadas      INTEGER NOT NULL,
    asistencia_pct              REAL,
    max_ausencias_consecutivas  INTEGER NOT NULL,
    episodios_ausencia          INTEGER NOT NULL,
    promedio                    REAL,
    asignaturas_reprobadas      INTEGER NOT NULL DEFAULT 0,
    aprobado                    INTEGER,
    nivel_alerta                TEXT NOT NULL CHECK (nivel_alerta IN ('prioritario','preventivo','regular')),
    motivos                     TEXT NOT NULL DEFAULT '[]',
    calculado_en                TEXT NOT NULL,
    PRIMARY KEY (estudiante_codigo, periodo_codigo)
);

CREATE TABLE IF NOT EXISTS ejecuciones_etl (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio          TEXT NOT NULL,
    fin             TEXT,
    estado          TEXT NOT NULL CHECK (estado IN ('en_curso','exitosa','con_advertencias','fallida')),
    disparador      TEXT NOT NULL,
    usuario         TEXT,
    leidos          INTEGER DEFAULT 0,
    aceptados       INTEGER DEFAULT 0,
    rechazados      INTEGER DEFAULT 0,
    omitidos        INTEGER DEFAULT 0,
    pasos           TEXT DEFAULT '[]',
    errores         TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS rechazos_etl (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id    INTEGER NOT NULL REFERENCES ejecuciones_etl(id),
    fuente          TEXT NOT NULL,
    archivo         TEXT,
    fila            INTEGER,
    motivo          TEXT NOT NULL,
    datos           TEXT
);

CREATE TABLE IF NOT EXISTS fuentes (
    nombre          TEXT PRIMARY KEY,
    entidad         TEXT NOT NULL,
    formato         TEXT NOT NULL,
    origen          TEXT,
    naturaleza      TEXT NOT NULL CHECK (naturaleza IN ('real','sintetica')),
    responsable     TEXT,
    descripcion     TEXT,
    ultima_carga    TEXT,
    registros       INTEGER DEFAULT 0,
    archivos        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS archivos_procesados (
    sha256          TEXT PRIMARY KEY,
    fuente          TEXT NOT NULL,
    archivo         TEXT NOT NULL,
    registros       INTEGER NOT NULL,
    aceptados       INTEGER NOT NULL,
    rechazados      INTEGER NOT NULL,
    ejecucion_id    INTEGER REFERENCES ejecuciones_etl(id),
    procesado_en    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS configuracion (
    clave           TEXT PRIMARY KEY,
    valor           TEXT NOT NULL,
    actualizado_en  TEXT,
    actualizado_por TEXT
);
"""

TABLES_IN_DEPENDENCY_ORDER = [
    "rechazos_etl", "archivos_procesados", "ejecuciones_etl",
    "indicadores", "calificaciones", "asistencias", "recursos_tecnologicos", "matriculas",
    "estudiantes", "periodos", "centros", "regiones", "fuentes",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or config.sqlite_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def session(path: Path | str | None = None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    seed_config(conn)
    conn.commit()


def reset_data(conn: sqlite3.Connection, keep_config: bool = False) -> None:
    """Vacía todas las tablas (F85: restablecer escenario inicial)."""
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in TABLES_IN_DEPENDENCY_ORDER:
        conn.execute(f"DELETE FROM {table}")
    if not keep_config:
        conn.execute("DELETE FROM configuracion")
    conn.execute("DELETE FROM sqlite_sequence")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    seed_config(conn)
    conn.commit()


# ---------------------------------------------------------------- configuración editable
def seed_config(conn: sqlite3.Connection) -> None:
    defaults = config.settings()
    flat = {}
    for section in config.EDITABLE_SECTIONS:
        flat.update(config.flatten({section: defaults[section]}))
    conn.executemany(
        "INSERT OR IGNORE INTO configuracion(clave, valor, actualizado_en, actualizado_por) VALUES (?,?,?,?)",
        [(k, json.dumps(v), now_iso(), "sistema") for k, v in flat.items()],
    )


def get_rules(conn: sqlite3.Connection) -> dict:
    """Umbrales vigentes: valores por defecto de YAML sobrescritos por la tabla configuracion."""
    defaults = config.settings()
    flat = {}
    for section in config.EDITABLE_SECTIONS:
        flat.update(config.flatten({section: defaults[section]}))
    for row in conn.execute("SELECT clave, valor FROM configuracion"):
        flat[row["clave"]] = json.loads(row["valor"])
    return config.unflatten(flat)


def set_rule(conn: sqlite3.Connection, clave: str, valor, usuario: str) -> None:
    conn.execute(
        """INSERT INTO configuracion(clave, valor, actualizado_en, actualizado_por) VALUES (?,?,?,?)
           ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor,
               actualizado_en=excluded.actualizado_en, actualizado_por=excluded.actualizado_por""",
        (clave, json.dumps(valor), now_iso(), usuario),
    )
    conn.commit()


# ---------------------------------------------------------------- utilidades de consulta
def query_df(conn: sqlite3.Connection, sql: str, params: tuple | list | dict = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn, params=params)


def upsert(conn: sqlite3.Connection, table: str, rows: list[dict], conflict: list[str]) -> int:
    """INSERT ... ON CONFLICT DO UPDATE: re-ejecutar el pipeline no duplica registros (F81)."""
    if not rows:
        return 0
    cols = list(rows[0].keys())
    updates = [c for c in cols if c not in conflict]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in updates) or None
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
        f"ON CONFLICT({', '.join(conflict)}) "
        + (f"DO UPDATE SET {set_clause}" if set_clause else "DO NOTHING")
    )
    conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
    return len(rows)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = ["regiones", "centros", "periodos", "estudiantes", "matriculas", "asistencias",
             "calificaciones", "recursos_tecnologicos", "indicadores", "ejecuciones_etl", "rechazos_etl"]
    return {n: conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in names}


def periods(conn: sqlite3.Connection) -> list[str]:
    """Períodos que ya tienen indicadores calculados, ordenados cronológicamente."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT p.codigo FROM periodos p JOIN indicadores i ON i.periodo_codigo=p.codigo "
        "ORDER BY p.anio, p.trimestre")]


def all_periods(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT codigo FROM periodos ORDER BY anio, trimestre")]
