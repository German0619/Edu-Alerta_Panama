"""Motor de alertas tempranas explicables (F32-F36).

La clasificación usa reglas transparentes y configurables; no es un modelo predictivo.
Cada alerta guarda los motivos que la activaron y requiere revisión humana.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

import pandas as pd
from pymongo import UpdateOne
from pymongo.database import Database

from edualerta.db import sql
from edualerta.services import audit

NIVELES = ["prioritario", "preventivo", "regular"]


def _isna(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v))


def classify(ind: dict, rules: dict) -> tuple[str, list[dict]]:
    """Devuelve (nivel, motivos). Cada criterio se evalúa primero contra el umbral crítico."""
    pr, pv = rules["alertas"]["prioritario"], rules["alertas"]["preventivo"]
    motivos = []
    checks = [
        ("asistencia", ind.get("asistencia_pct"), "asistencia_min", "<",
         lambda v, u: f"Asistencia de {v:.1f} % (umbral {u} %)"),
        ("promedio", ind.get("promedio"), "promedio_min", "<",
         lambda v, u: f"Promedio académico de {v:.1f}/100 (umbral {u})"),
        ("ausencias_consecutivas", ind.get("max_ausencias_consecutivas"), "ausencias_consecutivas", ">=",
         lambda v, u: f"{int(v)} ausencias consecutivas injustificadas (umbral {u})"),
    ]
    for criterio, valor, clave, op, texto in checks:
        if _isna(valor):
            continue
        for nivel, umbrales in (("prioritario", pr), ("preventivo", pv)):
            u = umbrales[clave]
            hit = valor < u if op == "<" else valor >= u
            if hit:
                motivos.append({"criterio": criterio, "nivel": nivel, "valor": float(valor), "umbral": u,
                                "texto": texto(valor, u)})
                break
    if any(m["nivel"] == "prioritario" for m in motivos):
        return "prioritario", motivos
    if motivos:
        return "preventivo", motivos
    return "regular", []


def alert_id(estudiante: str, periodo: str) -> str:
    return f"{estudiante}|{periodo}"


def sync_alerts(conn: sqlite3.Connection, db: Database, rules: dict) -> dict:
    """Crea/actualiza alertas en MongoDB de forma idempotente (F81) a partir de `indicadores`."""
    import json
    df = sql.query_df(conn, """SELECT i.*, c.region_codigo FROM indicadores i
                               JOIN centros c ON c.codigo=i.centro_codigo WHERE i.nivel_alerta != 'regular'""")
    now = datetime.now().replace(microsecond=0)
    existing = {d["_id"]: d for d in db.alertas.find({}, {"nivel": 1, "estado": 1, "vigente": 1})}
    ops, stats = [], {"nuevas": 0, "actualizadas": 0, "cambios_nivel": 0, "reabiertas": 0, "desactivadas": 0}
    current = set()
    for r in df.to_dict("records"):
        _id = alert_id(r["estudiante_codigo"], r["periodo_codigo"])
        current.add(_id)
        snapshot = {
            "estudiante_codigo": r["estudiante_codigo"], "periodo_codigo": r["periodo_codigo"],
            "centro_codigo": r["centro_codigo"], "region_codigo": r["region_codigo"], "grado": int(r["grado"]),
            "nivel": r["nivel_alerta"], "motivos": json.loads(r["motivos"]), "vigente": True,
            "indicadores": {k: (None if _isna(r[k]) else float(r[k])) for k in
                            ("asistencia_pct", "promedio", "max_ausencias_consecutivas", "ausencias_justificadas",
                             "asignaturas_reprobadas", "episodios_ausencia")},
            "actualizado_en": now,
        }
        prev = existing.get(_id)
        if prev is None:
            stats["nuevas"] += 1
            ops.append(UpdateOne({"_id": _id}, {"$set": snapshot, "$setOnInsert": {
                "estado": "abierta", "generada_en": now, "caso_id": None, "revision": None,
                "historial": [{"fecha": now, "evento": "generada", "usuario": "motor_reglas",
                               "detalle": f"Nivel {r['nivel_alerta']}"}]}}, upsert=True))
            continue
        update = {"$set": snapshot}
        events = []
        if prev.get("nivel") != r["nivel_alerta"]:
            stats["cambios_nivel"] += 1
            events.append({"fecha": now, "evento": "nivel_actualizado", "usuario": "motor_reglas",
                           "detalle": f"{prev.get('nivel')} → {r['nivel_alerta']}"})
            if prev.get("estado") == "descartada" and r["nivel_alerta"] == "prioritario":
                stats["reabiertas"] += 1
                snapshot["estado"] = "abierta"
                events.append({"fecha": now, "evento": "reabierta", "usuario": "motor_reglas",
                               "detalle": "Escaló a prioritario después de haber sido descartada"})
        if not prev.get("vigente", True):
            events.append({"fecha": now, "evento": "vigente_nuevamente", "usuario": "motor_reglas", "detalle": ""})
        if events:
            update["$push"] = {"historial": {"$each": events}}
        stats["actualizadas"] += 1
        ops.append(UpdateOne({"_id": _id}, update))
    for _id, prev in existing.items():
        if _id not in current and prev.get("vigente", True):
            stats["desactivadas"] += 1
            ops.append(UpdateOne({"_id": _id}, {"$set": {"vigente": False, "actualizado_en": now},
                                                 "$push": {"historial": {"fecha": now, "evento": "sin_criterios",
                                                                         "usuario": "motor_reglas",
                                                                         "detalle": "Ya no cumple criterios"}}}))
    if ops:
        db.alertas.bulk_write(ops, ordered=False)
    return stats


def alerts_frame(db: Database, periodo: str | None = None, niveles=None, estados=None, centros=None,
                 regiones=None, solo_vigentes: bool = True) -> pd.DataFrame:
    q: dict = {}
    if periodo:
        q["periodo_codigo"] = periodo
    if niveles:
        q["nivel"] = {"$in": list(niveles)}
    if estados:
        q["estado"] = {"$in": list(estados)}
    if centros:
        q["centro_codigo"] = {"$in": list(centros)}
    if regiones:
        q["region_codigo"] = {"$in": list(regiones)}
    if solo_vigentes:
        q["vigente"] = True
    docs = list(db.alertas.find(q))
    if not docs:
        return pd.DataFrame(columns=["_id", "estudiante_codigo", "periodo_codigo", "centro_codigo", "region_codigo",
                                     "grado", "nivel", "estado", "motivos", "caso_id", "asistencia_pct", "promedio",
                                     "max_ausencias_consecutivas"])
    df = pd.DataFrame(docs)
    ind = pd.json_normalize(df["indicadores"])
    df = pd.concat([df.drop(columns=["indicadores"]), ind], axis=1)
    df["nivel"] = pd.Categorical(df["nivel"], NIVELES, ordered=True)
    return df.sort_values(["nivel", "asistencia_pct"]).reset_index(drop=True)


def review_alert(db: Database, alerta_id: str, accion: str, motivo: str, usuario: str, perfil: str | None = None):
    """F36: confirmar o descartar una alerta documentando la justificación."""
    if accion not in ("confirmar", "descartar"):
        raise ValueError("Acción debe ser 'confirmar' o 'descartar'")
    if not motivo or len(motivo.strip()) < 5:
        raise ValueError("Debe documentar el motivo de la revisión (mínimo 5 caracteres).")
    alerta = db.alertas.find_one({"_id": alerta_id})
    if not alerta:
        raise ValueError("Alerta inexistente")
    if accion == "descartar" and alerta.get("caso_id"):
        raise ValueError("La alerta ya tiene un caso abierto; cierre el caso en lugar de descartarla.")
    now = datetime.now().replace(microsecond=0)
    estado = "confirmada" if accion == "confirmar" else "descartada"
    db.alertas.update_one({"_id": alerta_id}, {
        "$set": {"estado": estado, "revision": {"usuario": usuario, "fecha": now, "accion": accion,
                                                 "motivo": motivo.strip()}},
        "$push": {"historial": {"fecha": now, "evento": estado, "usuario": usuario, "detalle": motivo.strip()}}})
    audit.log(usuario, f"alerta_{estado}", "alertas", alerta_id,
              {"nivel": alerta["nivel"], "motivo": motivo.strip()}, perfil)
    return estado
