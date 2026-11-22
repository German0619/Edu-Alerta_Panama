"""Orquestador del pipeline ETL (F14, F19-F22, F79, F81, F82).

Orden: extracción -> limpieza/validación -> carga SQL (por dependencia de claves foráneas)
-> carga documental MongoDB -> integración y cálculo de indicadores -> alertas
-> recomendaciones. Cada paso queda en `ejecuciones_etl` y los rechazos en `rechazos_etl`.
"""
from __future__ import annotations

import json
import logging
import shutil
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from edualerta import config
from edualerta.db import mongo, sql
from edualerta.etl import extract, transform

log = logging.getLogger(__name__)

PROCESSED_GEOJSON = "regiones_procesadas.geojson"


def processed_geojson_path() -> Path:
    return config.sqlite_path().parent / PROCESSED_GEOJSON


def _write_geojson(batch: transform.Batch) -> None:
    feats = []
    for rec in batch.df.to_dict("records"):
        feats.append({"type": "Feature",
                      "properties": {"codigo": rec["codigo"], "nombre": rec["nombre"], "tipo": rec["tipo"]},
                      "geometry": json.loads(rec["_geometry"])})
    path = processed_geojson_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.exists():
        existing = {f["properties"]["codigo"]: f for f in json.loads(path.read_text("utf-8"))["features"]}
    existing.update({f["properties"]["codigo"]: f for f in feats})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": list(existing.values())},
                               ensure_ascii=False), encoding="utf-8")


def _load_mongo_observaciones(rows: list[dict]) -> int:
    db = mongo.require()
    ops = []
    for r in rows:
        doc = {"estudiante_codigo": r["estudiante_codigo"], "fecha": r["fecha"], "tipo": r["tipo"],
               "texto": r["texto"], "autor_rol": r["autor_rol"], "origen": "importacion"}
        ops.append(UpdateOne({"_id": r["id"]}, {"$set": doc, "$setOnInsert": {"registrado_en": sql.now_iso()}},
                             upsert=True))
    if ops:
        db.observaciones.bulk_write(ops, ordered=False)
    return len(ops)


def _running(conn) -> bool:
    limit = (datetime.now() - timedelta(minutes=30)).isoformat()
    return conn.execute("SELECT 1 FROM ejecuciones_etl WHERE estado='en_curso' AND inicio > ?",
                        (limit,)).fetchone() is not None


def process_source(conn, source: dict, run_id: int, force: bool) -> dict:
    """Procesa todos los archivos de una fuente. Un archivo defectuoso no detiene a los demás."""
    stats = {"fuente": source["nombre"], "archivos": 0, "omitidos": 0, "leidos": 0, "aceptados": 0,
             "rechazados": 0, "errores": []}
    cleaner = transform.CLEANERS[source["entidad"]]
    for path in extract.discover(source):
        digest = extract.file_hash(path)
        if not force and conn.execute("SELECT 1 FROM archivos_procesados WHERE sha256=?", (digest,)).fetchone():
            stats["omitidos"] += 1   # F81: archivo ya procesado, no se duplica
            continue
        stats["archivos"] += 1
        try:
            raw = extract.read_source(path, source["formato"])
            df = extract.normalize_columns(raw, source.get("alias"))
            missing = [c for c in source.get("requeridas", []) if c not in df.columns]
            if missing:
                raise extract.SourceError(f"Faltan columnas requeridas: {', '.join(missing)}")
            batch = transform.Batch(df, source["nombre"], path.name)
            rows = cleaner(batch, transform.RefData.load(conn))
            if source["entidad"] == "observaciones":
                _load_mongo_observaciones(rows)
            else:
                sql.upsert(conn, source["entidad"], rows, transform.CONFLICT_KEYS[source["entidad"]])
            if source["entidad"] == "regiones":
                _write_geojson(batch)
            conn.executemany(
                "INSERT INTO rechazos_etl(ejecucion_id, fuente, archivo, fila, motivo, datos) VALUES (?,?,?,?,?,?)",
                [(run_id, source["nombre"], path.name, r["fila"], r["motivo"], r["datos"]) for r in batch.rejects])
            conn.execute(
                "INSERT OR REPLACE INTO archivos_procesados VALUES (?,?,?,?,?,?,?,?)",
                (digest, source["nombre"], path.name, batch.leidos, len(rows), len(batch.rejects), run_id,
                 sql.now_iso()))
            conn.commit()
            stats["leidos"] += batch.leidos
            stats["aceptados"] += len(rows)
            stats["rechazados"] += len(batch.rejects)
        except (extract.SourceError, mongo.MongoUnavailable, PyMongoError, ValueError, KeyError) as exc:
            conn.rollback()
            msg = f"{path.name}: {exc}"
            log.warning("Fuente %s con error: %s", source["nombre"], msg)
            stats["errores"].append(msg)
            conn.execute(
                "INSERT INTO rechazos_etl(ejecucion_id, fuente, archivo, fila, motivo, datos) VALUES (?,?,?,?,?,?)",
                (run_id, source["nombre"], path.name, None, f"Archivo no procesado: {exc}", None))
            conn.commit()

    # F13 / F76: metadatos de la fuente
    table = "observaciones" if source["entidad"] == "observaciones" else source["entidad"]
    if table == "observaciones":
        try:
            registros = mongo.require().observaciones.count_documents({"origen": "importacion"})
        except (mongo.MongoUnavailable, PyMongoError):
            registros = None
    else:
        registros = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    n_files = conn.execute("SELECT COUNT(*) FROM archivos_procesados WHERE fuente=?", (source["nombre"],)).fetchone()[0]
    conn.execute(
        """INSERT INTO fuentes(nombre, entidad, formato, origen, naturaleza, responsable, descripcion,
                               ultima_carga, registros, archivos)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(nombre) DO UPDATE SET entidad=excluded.entidad, formato=excluded.formato,
               origen=excluded.origen, naturaleza=excluded.naturaleza, responsable=excluded.responsable,
               descripcion=excluded.descripcion,
               ultima_carga=CASE WHEN ? > 0 THEN excluded.ultima_carga ELSE fuentes.ultima_carga END,
               registros=COALESCE(excluded.registros, fuentes.registros), archivos=excluded.archivos""",
        (source["nombre"], source["entidad"], source["formato"], source["origen"], source["naturaleza"],
         source["responsable"], source["descripcion"], sql.now_iso(), registros, n_files, stats["archivos"]))
    conn.commit()
    return stats


def run(trigger: str = "manual", usuario: str = "sistema", force: bool = False,
        conn=None, perfil: str | None = None) -> dict:
    """Ejecuta el pipeline completo (F79). Devuelve el resumen de la ejecución."""
    from edualerta.services import alerts, audit, indicators, recommendations

    own_conn = conn is None
    conn = conn or sql.connect()
    sql.init_schema(conn)
    if _running(conn):
        return {"estado": "omitida", "mensaje": "Ya hay una ejecución en curso."}

    cur = conn.execute("INSERT INTO ejecuciones_etl(inicio, estado, disparador, usuario) VALUES (?,?,?,?)",
                       (sql.now_iso(), "en_curso", trigger, usuario))
    run_id = cur.lastrowid
    conn.commit()
    pasos, errores = [], []
    tot = {"leidos": 0, "aceptados": 0, "rechazados": 0, "omitidos": 0}

    def step(nombre, fn):
        t0 = time.perf_counter()
        try:
            detalle = fn()
            pasos.append({"paso": nombre, "estado": "ok", "segundos": round(time.perf_counter() - t0, 2),
                          "detalle": detalle})
            return detalle
        except Exception as exc:  # F82: un paso fallido se registra y el resto continúa
            conn.rollback()
            log.exception("Paso %s falló", nombre)
            pasos.append({"paso": nombre, "estado": "error", "segundos": round(time.perf_counter() - t0, 2),
                          "detalle": str(exc)})
            errores.append(f"{nombre}: {exc}")
            return None

    try:
        for source in config.sources():
            st = step(f"Extraer y validar · {source['nombre']}", lambda s=source: process_source(conn, s, run_id, force))
            if st:
                for k in tot:
                    tot[k] += st[k]
                errores.extend(st["errores"])
        rules = sql.get_rules(conn)
        step("Integrar y calcular indicadores", lambda: indicators.compute_all(conn, rules))
        step("Sincronizar alertas en MongoDB", lambda: alerts.sync_alerts(conn, mongo.require(), rules))
        step("Generar recomendaciones", lambda: recommendations.generate(conn, mongo.require(), rules))
        estado = "exitosa" if not errores else "con_advertencias"
    except Exception as exc:
        estado = "fallida"
        errores.append(f"{exc}\n{traceback.format_exc(limit=3)}")

    conn.execute(
        "UPDATE ejecuciones_etl SET fin=?, estado=?, leidos=?, aceptados=?, rechazados=?, omitidos=?, pasos=?, "
        "errores=? WHERE id=?",
        (sql.now_iso(), estado, tot["leidos"], tot["aceptados"], tot["rechazados"], tot["omitidos"],
         json.dumps(pasos, ensure_ascii=False, default=str), json.dumps(errores, ensure_ascii=False), run_id))
    conn.commit()
    summary = {"id": run_id, "estado": estado, **tot, "pasos": pasos, "errores": errores}
    audit.log(usuario, "ejecutar_pipeline", "ejecuciones_etl", str(run_id),
              {"disparador": trigger, "estado": estado, **tot}, perfil)
    if own_conn:
        conn.close()
    return summary


def save_upload(source_name: str, filename: str, data: bytes) -> Path:
    """Guarda un archivo subido desde la interfaz para que el pipeline lo procese."""
    safe = Path(filename).name.replace(" ", "_")
    dest = extract.incoming_dir(source_name)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"{datetime.now():%Y%m%d%H%M%S}_{safe}"
    target.write_bytes(data)
    return target


def stage_demo_package() -> list[str]:
    """Copia el paquete demo 2026-T1 a incoming (simula la entrega de una nueva carga)."""
    copied = []
    for source in config.sources():
        for path in sorted(config.DEMO_DIR.glob(source["patron"])):
            dest = extract.incoming_dir(source["nombre"])
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest / path.name)
            copied.append(path.name)
    return copied
