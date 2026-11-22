"""Rutas, variables de entorno y carga de archivos de configuración YAML."""
from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DEMO_DIR = DATA_DIR / "demo"
INCOMING_DIR = DATA_DIR / "incoming"


def sqlite_path() -> Path:
    return Path(os.environ.get("SQLITE_PATH", DATA_DIR / "db" / "edualerta.db"))


def mongo_uri() -> str:
    return os.environ.get("MONGO_URI", "mongodb://localhost:27017")


def mongo_db_name() -> str:
    return os.environ.get("MONGO_DB", "edualerta")


def demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD", "edualerta")


@lru_cache(maxsize=None)
def _load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def settings() -> dict:
    """Copia de config/settings.yaml (los valores editables viven luego en SQL)."""
    data = copy.deepcopy(_load_yaml("settings.yaml"))
    env_interval = os.environ.get("ETL_INTERVAL_MINUTES")
    if env_interval and env_interval.isdigit():
        data["pipeline"]["intervalo_minutos"] = int(env_interval)
    return data


def sources() -> list[dict]:
    return copy.deepcopy(_load_yaml("sources.yaml")["fuentes"])


def kpi_catalog() -> dict:
    return copy.deepcopy(_load_yaml("kpis.yaml")["kpis"])


def risk_matrix() -> list[dict]:
    return copy.deepcopy(_load_yaml("riesgos.yaml")["riesgos"])


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def unflatten(flat: dict) -> dict:
    out: dict = {}
    for key, value in flat.items():
        node = out
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
    return out


# Secciones de settings.yaml que se pueden editar en caliente desde Administración
EDITABLE_SECTIONS = ("alertas", "tecnologia", "recomendaciones", "pipeline")
