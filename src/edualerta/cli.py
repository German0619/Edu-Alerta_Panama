"""Línea de comandos: bootstrap, pipeline, reset y generación de datos (F79, F85).

    python -m edualerta.cli bootstrap        # esquema + índices + datos demo + 1ª ejecución
    python -m edualerta.cli pipeline [--force]
    python -m edualerta.cli reset            # restablece el escenario inicial de demostración
    python -m edualerta.cli generate         # regenera los archivos sintéticos
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time

from edualerta import config, datagen
from edualerta.db import mongo, sql
from edualerta.etl import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("edualerta")


def wait_for_mongo(seconds: int = 60) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if mongo.ping():
            return True
        time.sleep(2)
    return False


def bootstrap() -> dict:
    datagen.ensure_generated()
    with sql.session() as conn:
        sql.init_schema(conn)
        has_run = conn.execute("SELECT 1 FROM ejecuciones_etl WHERE estado IN ('exitosa','con_advertencias')"
                               ).fetchone()
    if not wait_for_mongo():
        log.error("MongoDB no responde; la aplicación arrancará en modo degradado.")
        return {"estado": "mongo_no_disponible"}
    mongo.ensure_indexes()
    if has_run:
        log.info("Base ya inicializada; no se re-ejecuta el pipeline.")
        return {"estado": "ya_inicializada"}
    summary = pipeline.run(trigger="bootstrap", usuario="sistema")
    log.info("Pipeline inicial: %s", {k: summary[k] for k in ("estado", "leidos", "aceptados", "rechazados")})
    return summary


def reset() -> dict:
    """F85: vacía SQL, MongoDB y cargas subidas; recarga la carga base 2025."""
    with sql.session() as conn:
        sql.init_schema(conn)
        sql.reset_data(conn)
    if not wait_for_mongo(20):
        raise SystemExit("MongoDB no disponible")
    mongo.reset()
    from edualerta.services import audit
    audit.clear_fallback()
    if config.INCOMING_DIR.exists():
        for child in config.INCOMING_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
    geo = pipeline.processed_geojson_path()
    if geo.exists():
        geo.unlink()
    datagen.generate()
    summary = pipeline.run(trigger="restablecer_demo", usuario="sistema")
    audit.log("sistema", "restablecer_demo", "sistema", None, {"estado": summary["estado"]})
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edualerta")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap")
    p = sub.add_parser("pipeline")
    p.add_argument("--force", action="store_true", help="reprocesa archivos ya cargados (sin duplicar)")
    sub.add_parser("reset")
    sub.add_parser("generate")
    args = parser.parse_args(argv)

    if args.cmd == "bootstrap":
        out = bootstrap()
    elif args.cmd == "pipeline":
        wait_for_mongo(30)
        out = pipeline.run(trigger="manual_cli", force=args.force)
    elif args.cmd == "reset":
        out = reset()
    else:
        out = datagen.generate()
    print(json.dumps({k: v for k, v in out.items() if k != "pasos"}, ensure_ascii=False, indent=2, default=str))
    return 0 if out.get("estado") != "fallida" else 1


if __name__ == "__main__":
    sys.exit(main())
