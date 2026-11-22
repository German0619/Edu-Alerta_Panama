"""Limpieza, normalización y validación de reglas de negocio (F15-F18).

Cada fuente pasa por un `Batch`: los registros inválidos no detienen la carga, se
apartan con el motivo exacto y quedan en `rechazos_etl` para el reporte de calidad.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

import pandas as pd

ESTADOS_ASISTENCIA = {
    "presente": "presente", "p": "presente", "asistio": "presente", "1": "presente",
    "ausente": "ausente", "a": "ausente", "falta": "ausente", "0": "ausente",
    "justificada": "justificada", "j": "justificada", "ausencia_justificada": "justificada",
    "tardanza": "tardanza", "t": "tardanza", "tarde": "tardanza",
}
BOOL_MAP = {"si": 1, "sí": 1, "s": 1, "yes": 1, "true": 1, "1": 1, "no": 0, "n": 0, "false": 0, "0": 0}
GENERO_MAP = {"f": "F", "femenino": "F", "mujer": "F", "m": "M", "masculino": "M", "hombre": "M"}
TIPOS_SEGUIMIENTO = {"observacion", "diagnostico", "intervencion"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


@dataclass
class Batch:
    df: pd.DataFrame
    fuente: str
    archivo: str
    rejects: list[dict] = field(default_factory=list)
    leidos: int = 0

    def __post_init__(self):
        self.leidos = len(self.df)
        self.df = self.df.copy()
        self.df["_fila"] = range(2, len(self.df) + 2)  # número de línea del archivo (encabezado = 1)
        for col in self.df.columns:
            if col.startswith("_"):
                continue
            s = self.df[col]
            self.df[col] = s.where(s.isna(), s.astype(str).str.strip())
            self.df[col] = self.df[col].replace({"": None, "nan": None, "None": None})

    def reject(self, mask: pd.Series, motivo: str) -> None:
        mask = mask.fillna(True).astype(bool)
        if not mask.any():
            return
        for rec in self.df[mask].to_dict("records"):
            fila = rec.pop("_fila")
            datos = {k: v for k, v in rec.items() if not str(k).startswith("_")}
            self.rejects.append({"fila": int(fila), "motivo": motivo,
                                 "datos": json.dumps(datos, ensure_ascii=False, default=str)})
        self.df = self.df[~mask]

    def require(self, cols: list[str]) -> None:
        for c in cols:
            if c in self.df.columns:
                self.reject(self.df[c].isna(), f"Campo requerido vacío: {c}")

    def dedupe(self, keys: list[str] | None = None) -> None:
        cols = [c for c in self.df.columns if not c.startswith("_")]
        self.reject(self.df.duplicated(subset=cols, keep="first"), "Registro duplicado exacto")
        if keys:
            self.reject(self.df.duplicated(subset=keys, keep="last"),
                        f"Clave repetida ({', '.join(keys)}); se conserva la última versión")


# --------------------------------------------------------------------------- normalizadores
def norm_student(s: pd.Series) -> pd.Series:
    """'e42', 'E-42', ' e-0042 ' -> 'E-0042'; inválidos -> None."""
    def f(x):
        if x is None or pd.isna(x):
            return None
        m = re.fullmatch(r"E[-_ ]?0*(\d{1,4})", str(x).strip().upper())
        return f"E-{int(m.group(1)):04d}" if m else None
    return s.map(f)


def norm_center(s: pd.Series) -> pd.Series:
    def f(x):
        if x is None or pd.isna(x):
            return None
        m = re.fullmatch(r"CE[-_ ]?0*(\d{1,3})", str(x).strip().upper())
        return f"CE-{int(m.group(1)):03d}" if m else None
    return s.map(f)


def norm_code(s: pd.Series) -> pd.Series:
    return s.map(lambda x: None if x is None or pd.isna(x) else str(x).strip().upper())


def parse_dates(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        pending = out.isna() & s.notna()
        if not pending.any():
            break
        out.loc[pending] = pd.to_datetime(s[pending], format=fmt, errors="coerce")
    return out


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.replace(",", ".", regex=False), errors="coerce")


def _lower_map(s: pd.Series, mapping: dict) -> pd.Series:
    return s.map(lambda x: None if x is None or pd.isna(x) else mapping.get(str(x).strip().lower()))


# --------------------------------------------------------------------------- contexto de referencia
@dataclass
class RefData:
    regiones: set
    centros: set
    estudiantes: set
    periodos: pd.DataFrame
    matriculas: set  # "E-0001|2025-T1"

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> "RefData":
        per = pd.read_sql_query("SELECT codigo, fecha_inicio, fecha_fin FROM periodos", conn)
        per["fecha_inicio"] = pd.to_datetime(per["fecha_inicio"])
        per["fecha_fin"] = pd.to_datetime(per["fecha_fin"])
        return cls(
            regiones={r[0] for r in conn.execute("SELECT codigo FROM regiones")},
            centros={r[0] for r in conn.execute("SELECT codigo FROM centros")},
            estudiantes={r[0] for r in conn.execute("SELECT codigo FROM estudiantes")},
            periodos=per,
            matriculas={f"{a}|{b}" for a, b in conn.execute(
                "SELECT estudiante_codigo, periodo_codigo FROM matriculas")},
        )


# --------------------------------------------------------------------------- limpiadores por entidad
def clean_regiones(b: Batch, ref: RefData) -> list[dict]:
    b.require(["codigo", "nombre"])
    b.df["codigo"] = norm_code(b.df["codigo"])
    if "tipo" not in b.df:
        b.df["tipo"] = "provincial"
    b.df["tipo"] = b.df["tipo"].fillna("provincial").str.lower()
    b.reject(~b.df["tipo"].isin(["provincial", "comarcal", "metropolitana"]), "Tipo de región no válido")
    b.dedupe(["codigo"])
    return b.df[["codigo", "nombre", "tipo"]].to_dict("records")


def clean_centros(b: Batch, ref: RefData) -> list[dict]:
    b.require(["codigo", "nombre", "region_codigo", "zona", "dependencia"])
    b.df["codigo"] = norm_center(b.df["codigo"])
    b.reject(b.df["codigo"].isna(), "Código de centro con formato inválido (esperado CE-NNN)")
    b.df["region_codigo"] = norm_code(b.df["region_codigo"])
    b.reject(~b.df["region_codigo"].isin(ref.regiones), "Región inexistente")
    b.df["zona"] = b.df["zona"].str.lower()
    b.reject(~b.df["zona"].isin(["urbana", "rural"]), "Zona debe ser urbana o rural")
    b.df["dependencia"] = b.df["dependencia"].str.lower()
    b.reject(~b.df["dependencia"].isin(["oficial", "particular"]), "Dependencia debe ser oficial o particular")
    if "nivel" not in b.df:
        b.df["nivel"] = "premedia"
    b.df["nivel"] = b.df["nivel"].fillna("premedia").str.lower()
    b.reject(~b.df["nivel"].isin(["primaria", "premedia", "media"]), "Nivel educativo no válido")
    b.dedupe(["codigo"])
    return b.df[["codigo", "nombre", "region_codigo", "zona", "dependencia", "nivel"]].to_dict("records")


def clean_periodos(b: Batch, ref: RefData) -> list[dict]:
    b.require(["codigo", "anio", "trimestre", "fecha_inicio", "fecha_fin"])
    b.df["codigo"] = norm_code(b.df["codigo"])
    b.df["anio"] = to_number(b.df["anio"])
    b.df["trimestre"] = to_number(b.df["trimestre"])
    b.reject(~b.df["trimestre"].isin([1, 2, 3]), "Trimestre debe ser 1, 2 o 3")
    b.reject(~b.df["anio"].between(2000, 2100), "Año fuera de rango")
    ini, fin = parse_dates(b.df["fecha_inicio"]), parse_dates(b.df["fecha_fin"])
    b.df["fecha_inicio"], b.df["fecha_fin"] = ini, fin
    b.reject(b.df["fecha_inicio"].isna() | b.df["fecha_fin"].isna(), "Fecha de período inválida")
    b.reject(b.df["fecha_inicio"] >= b.df["fecha_fin"], "La fecha de inicio debe ser anterior a la de fin")
    b.dedupe(["codigo"])
    out = b.df.copy()
    out["anio"] = out["anio"].astype(int)
    out["trimestre"] = out["trimestre"].astype(int)
    out["fecha_inicio"] = out["fecha_inicio"].dt.strftime("%Y-%m-%d")
    out["fecha_fin"] = out["fecha_fin"].dt.strftime("%Y-%m-%d")
    return out[["codigo", "anio", "trimestre", "fecha_inicio", "fecha_fin"]].to_dict("records")


def clean_estudiantes(b: Batch, ref: RefData) -> list[dict]:
    b.require(["codigo", "genero", "anio_nacimiento"])
    b.df["codigo"] = norm_student(b.df["codigo"])
    b.reject(b.df["codigo"].isna(), "Código anónimo inválido (esperado E-NNNN)")
    b.df["genero"] = _lower_map(b.df["genero"], GENERO_MAP)
    b.reject(b.df["genero"].isna(), "Género no reconocido")
    b.df["anio_nacimiento"] = to_number(b.df["anio_nacimiento"])
    b.reject(~b.df["anio_nacimiento"].between(1990, 2025), "Año de nacimiento fuera de rango")
    b.dedupe(["codigo"])
    out = b.df.copy()
    out["anio_nacimiento"] = out["anio_nacimiento"].astype(int)
    out["sintetico"] = 1
    return out[["codigo", "genero", "anio_nacimiento", "sintetico"]].to_dict("records")


def clean_matriculas(b: Batch, ref: RefData) -> list[dict]:
    b.require(["estudiante_codigo", "centro_codigo", "periodo_codigo", "grado"])
    b.df["estudiante_codigo"] = norm_student(b.df["estudiante_codigo"])
    b.df["centro_codigo"] = norm_center(b.df["centro_codigo"])
    b.df["periodo_codigo"] = norm_code(b.df["periodo_codigo"])
    b.reject(~b.df["estudiante_codigo"].isin(ref.estudiantes), "Estudiante no registrado")
    b.reject(~b.df["centro_codigo"].isin(ref.centros), "Centro educativo inexistente")
    b.reject(~b.df["periodo_codigo"].isin(set(ref.periodos["codigo"])), "Período inexistente")
    b.df["grado"] = to_number(b.df["grado"])
    b.reject(~b.df["grado"].between(1, 12), "Grado fuera de rango (1-12)")
    if "estado" not in b.df:
        b.df["estado"] = "activa"
    b.df["estado"] = b.df["estado"].fillna("activa").str.lower()
    b.reject(~b.df["estado"].isin(["activa", "retirada", "trasladada"]), "Estado de matrícula no válido")
    b.dedupe(["estudiante_codigo", "periodo_codigo"])
    out = b.df.copy()
    out["grado"] = out["grado"].astype(int)
    return out[["estudiante_codigo", "centro_codigo", "periodo_codigo", "grado", "estado"]].to_dict("records")


def clean_recursos(b: Batch, ref: RefData) -> list[dict]:
    b.require(["centro_codigo", "periodo_codigo", "tiene_internet", "computadoras_funcionales",
               "tabletas_funcionales"])
    b.df["centro_codigo"] = norm_center(b.df["centro_codigo"])
    b.df["periodo_codigo"] = norm_code(b.df["periodo_codigo"])
    b.reject(~b.df["centro_codigo"].isin(ref.centros), "Centro educativo inexistente")
    b.reject(~b.df["periodo_codigo"].isin(set(ref.periodos["codigo"])), "Período inexistente")
    b.df["tiene_internet"] = _lower_map(b.df["tiene_internet"], BOOL_MAP)
    b.reject(b.df["tiene_internet"].isna(), "Valor de internet no reconocido (si/no)")
    if "velocidad_mbps" not in b.df:
        b.df["velocidad_mbps"] = "0"
    for col in ("velocidad_mbps", "computadoras_funcionales", "tabletas_funcionales"):
        b.df[col] = to_number(b.df[col].fillna("0"))
        b.reject(b.df[col].isna() | (b.df[col] < 0), f"{col} debe ser un número no negativo")
    b.dedupe(["centro_codigo", "periodo_codigo"])
    out = b.df.copy()
    for col in ("tiene_internet", "computadoras_funcionales", "tabletas_funcionales"):
        out[col] = out[col].astype(int)
    out["velocidad_mbps"] = out["velocidad_mbps"].astype(float)
    out["actualizado_por"] = "etl"
    out["actualizado_en"] = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S")
    return out[["centro_codigo", "periodo_codigo", "tiene_internet", "velocidad_mbps", "computadoras_funcionales",
                "tabletas_funcionales", "actualizado_por", "actualizado_en"]].to_dict("records")


def _assign_period(fechas: pd.Series, periodos: pd.DataFrame) -> pd.Series:
    out = pd.Series(None, index=fechas.index, dtype=object)
    for _, p in periodos.iterrows():
        out[(fechas >= p["fecha_inicio"]) & (fechas <= p["fecha_fin"])] = p["codigo"]
    return out


def clean_asistencias(b: Batch, ref: RefData) -> list[dict]:
    b.require(["estudiante_codigo", "fecha", "estado"])
    b.df["estudiante_codigo"] = norm_student(b.df["estudiante_codigo"])
    b.reject(~b.df["estudiante_codigo"].isin(ref.estudiantes), "Asistencia de estudiante no registrado")
    b.df["fecha"] = parse_dates(b.df["fecha"])
    b.reject(b.df["fecha"].isna(), "Fecha inválida o con formato no reconocido")
    b.df["estado"] = _lower_map(b.df["estado"], ESTADOS_ASISTENCIA)
    b.reject(b.df["estado"].isna(), "Estado de asistencia no reconocido")
    assigned = _assign_period(b.df["fecha"], ref.periodos)
    if "periodo_codigo" in b.df:
        declared = norm_code(b.df["periodo_codigo"])
        b.df["_periodo"] = assigned
        b.reject(declared.notna() & (declared != assigned), "La fecha no corresponde al período declarado")
        assigned = b.df["_periodo"]
    b.df["periodo_codigo"] = assigned
    b.reject(b.df["periodo_codigo"].isna(), "La fecha no pertenece a ningún período académico")
    b.reject(~(b.df["estudiante_codigo"] + "|" + b.df["periodo_codigo"]).isin(ref.matriculas),
             "Estudiante sin matrícula en el período")
    b.df["fecha"] = b.df["fecha"].dt.strftime("%Y-%m-%d")
    b.dedupe(["estudiante_codigo", "fecha"])
    return b.df[["estudiante_codigo", "periodo_codigo", "fecha", "estado"]].to_dict("records")


def clean_calificaciones(b: Batch, ref: RefData) -> list[dict]:
    b.require(["estudiante_codigo", "periodo_codigo", "asignatura", "nota"])
    b.df["estudiante_codigo"] = norm_student(b.df["estudiante_codigo"])
    b.df["periodo_codigo"] = norm_code(b.df["periodo_codigo"])
    b.reject(~b.df["estudiante_codigo"].isin(ref.estudiantes), "Calificación de estudiante no registrado")
    b.reject(~b.df["periodo_codigo"].isin(set(ref.periodos["codigo"])), "Período inexistente")
    b.reject(~(b.df["estudiante_codigo"] + "|" + b.df["periodo_codigo"]).isin(ref.matriculas),
             "Estudiante sin matrícula en el período")
    b.df["nota"] = to_number(b.df["nota"])
    b.reject(b.df["nota"].isna(), "Nota no numérica")
    b.reject(~b.df["nota"].between(0, 100), "Nota fuera del rango 0-100")
    b.df["asignatura"] = b.df["asignatura"].str.strip()
    b.dedupe(["estudiante_codigo", "periodo_codigo", "asignatura"])
    out = b.df.copy()
    out["nota"] = out["nota"].astype(float)
    return out[["estudiante_codigo", "periodo_codigo", "asignatura", "nota"]].to_dict("records")


def clean_observaciones(b: Batch, ref: RefData) -> list[dict]:
    b.require(["id", "estudiante_codigo", "fecha", "tipo", "texto"])
    b.df["estudiante_codigo"] = norm_student(b.df["estudiante_codigo"])
    b.reject(~b.df["estudiante_codigo"].isin(ref.estudiantes), "Documento de estudiante no registrado")
    b.df["fecha"] = parse_dates(b.df["fecha"])
    b.reject(b.df["fecha"].isna(), "Fecha inválida")
    b.df["tipo"] = b.df["tipo"].str.lower()
    b.reject(~b.df["tipo"].isin(TIPOS_SEGUIMIENTO), "Tipo debe ser observacion, diagnostico o intervencion")
    b.dedupe(["id"])
    out = b.df.copy()
    out["fecha"] = out["fecha"].dt.strftime("%Y-%m-%d")
    if "autor_rol" not in out:
        out["autor_rol"] = "docente"
    return out[["id", "estudiante_codigo", "fecha", "tipo", "texto", "autor_rol"]].to_dict("records")


CLEANERS = {
    "regiones": clean_regiones,
    "centros": clean_centros,
    "periodos": clean_periodos,
    "estudiantes": clean_estudiantes,
    "matriculas": clean_matriculas,
    "recursos_tecnologicos": clean_recursos,
    "asistencias": clean_asistencias,
    "calificaciones": clean_calificaciones,
    "observaciones": clean_observaciones,
}

CONFLICT_KEYS = {
    "regiones": ["codigo"],
    "centros": ["codigo"],
    "periodos": ["codigo"],
    "estudiantes": ["codigo"],
    "matriculas": ["estudiante_codigo", "periodo_codigo"],
    "recursos_tecnologicos": ["centro_codigo", "periodo_codigo"],
    "asistencias": ["estudiante_codigo", "fecha"],
    "calificaciones": ["estudiante_codigo", "periodo_codigo", "asignatura"],
}
