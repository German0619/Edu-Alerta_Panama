"""Extracción de fuentes CSV, JSON y GeoJSON (F07-F12, F14)."""
from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

from edualerta import config


class SourceError(ValueError):
    """Archivo ilegible o con estructura incorrecta (se registra sin detener el pipeline)."""


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-zA-Z]+", "_", text.strip().lower()).strip("_")


def normalize_columns(df: pd.DataFrame, alias: dict | None = None) -> pd.DataFrame:
    """F16: encabezados en minúscula, sin tildes, con guion bajo y mapeados por alias."""
    alias = {normalize_name(k): v for k, v in (alias or {}).items()}
    cols = [c if str(c).startswith("_") else normalize_name(c) for c in df.columns]  # "_x" = columnas internas
    cols = [alias.get(c, c) for c in cols]
    out = df.copy()
    out.columns = cols
    return out.loc[:, ~out.columns.duplicated()]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def incoming_dir(source_name: str) -> Path:
    return config.INCOMING_DIR / source_name


def discover(source: dict) -> list[Path]:
    """Archivos de la carga base (data/raw) + archivos subidos por la interfaz (data/incoming/<fuente>)."""
    files = sorted(config.RAW_DIR.glob(source["patron"]))
    inc = incoming_dir(source["nombre"])
    if inc.exists():
        ext = {"csv": "*.csv", "json": "*.json", "geojson": "*.geojson"}[source["formato"]]
        files += sorted(inc.glob(ext))
    return files


def _read_bytes(data: bytes, formato: str) -> tuple[pd.DataFrame, dict | None]:
    try:
        if formato == "csv":
            text = data.decode("utf-8-sig")
            sep = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
            return pd.read_csv(io.StringIO(text), dtype=str, sep=sep, skipinitialspace=True), None
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, pd.errors.ParserError, IndexError) as exc:
        raise SourceError(f"No se pudo leer el archivo como {formato.upper()}: {exc}") from exc

    if formato == "geojson":
        if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
            raise SourceError("El GeoJSON debe ser un FeatureCollection con 'features'.")
        rows = [dict(f.get("properties") or {}) for f in payload["features"]]
        for row, feat in zip(rows, payload["features"]):
            row["_geometry"] = json.dumps(feat.get("geometry"))
        return pd.DataFrame(rows), payload
    if isinstance(payload, dict):
        payload = payload.get("documentos") or payload.get("data") or [payload]
    if not isinstance(payload, list):
        raise SourceError("El JSON debe contener una lista de documentos.")
    if not all(isinstance(d, dict) for d in payload):
        raise SourceError("Cada elemento del JSON debe ser un documento (objeto).")
    return pd.DataFrame(payload, dtype=object), None


def read_source(path: Path, formato: str) -> pd.DataFrame:
    df, _ = _read_bytes(Path(path).read_bytes(), formato)
    return df


def preview(data: bytes, source: dict, rows: int = 10) -> dict:
    """F11 + F12: vista previa con encabezados normalizados y verificación de columnas requeridas."""
    df, _ = _read_bytes(data, source["formato"])
    norm = normalize_columns(df, source.get("alias"))
    required = source.get("requeridas", [])
    missing = [c for c in required if c not in norm.columns]
    return {
        "registros": len(df),
        "columnas_originales": list(df.columns),
        "columnas_normalizadas": list(norm.columns),
        "faltantes": missing,
        "valido": not missing,
        "muestra": norm.drop(columns=[c for c in norm.columns if c.startswith("_")]).head(rows),
    }


def detect_source(filename: str) -> dict | None:
    """Sugiere la fuente según el nombre del archivo (patrón configurado)."""
    from fnmatch import fnmatch
    for s in config.sources():
        if fnmatch(filename.lower(), s["patron"].lower()):
            return s
    return None
