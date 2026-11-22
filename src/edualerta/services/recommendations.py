"""Recomendaciones por reglas explícitas y registro de decisiones humanas (F65-F71).

El sistema distingue:
  * Recomendación automática (`generada_por = motor_reglas`): sugiere, nunca ejecuta.
  * Decisión gerencial (`decision.registrada_por = <usuario>`): aprobación humana con
    responsable, justificación, fecha de revisión y evaluación de riesgos.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pandas as pd
from pymongo import UpdateOne
from pymongo.database import Database

from edualerta.db import sql
from edualerta.services import audit, indicators, regional, tech

URGENCIA = {"alta": 3, "media": 2, "baja": 1}
ACCIONES = {"aprobar": "aprobada", "posponer": "pospuesta", "rechazar": "rechazada",
            "solicitar_revision": "en revisión"}
CUMPLIMIENTO = ["no iniciada", "en curso", "cumplida", "incumplida"]


def risk_level(prob: int, impacto: int) -> str:
    score = prob * impacto
    return "alto" if score >= 15 else "medio" if score >= 8 else "bajo"


def _rec(regla, objetivo_tipo, objetivo_codigo, objetivo_nombre, periodo, titulo, descripcion, criterio,
         evidencias, urgencia, alcance):
    return {"regla": regla, "regla_clave": f"{regla}:{objetivo_codigo}:{periodo}", "periodo_codigo": periodo,
            "objetivo": {"tipo": objetivo_tipo, "codigo": objetivo_codigo, "nombre": objetivo_nombre},
            "titulo": titulo, "descripcion": descripcion, "criterio": criterio, "evidencias": evidencias,
            "urgencia": urgencia, "alcance": int(alcance)}


def build(conn: sqlite3.Connection, db: Database, rules: dict, periodo: str | None = None) -> list[dict]:
    """F65-F66: aplica las reglas y adjunta la evidencia que justifica cada recomendación."""
    per = sql.periods(conn)
    if not per:
        return []
    periodo = periodo or per[-1]
    rr = rules["recomendaciones"]
    recs = []
    ind = indicators.indicator_frame(conn, periodo)
    if ind.empty:
        return []

    # R-TUT: concentración de estudiantes prioritarios en un centro
    by_c = ind.groupby(["centro_codigo", "centro_nombre"]).agg(
        n=("estudiante_codigo", "count"), prio=("nivel_alerta", lambda s: (s == "prioritario").sum()),
        asis=("asistencia_pct", "mean"), prom=("promedio", "mean")).reset_index()
    by_c["pct"] = by_c["prio"] / by_c["n"] * 100
    for r in by_c[by_c["pct"] >= rr["pct_prioritarios_centro"]].itertuples():
        recs.append(_rec("R-TUT", "centro", r.centro_codigo, r.centro_nombre, periodo,
                         f"Reforzar tutorías y seguimiento en {r.centro_nombre}",
                         "Asignar tutores y priorizar la revisión de los casos prioritarios del centro.",
                         f"% de estudiantes prioritarios ≥ {rr['pct_prioritarios_centro']} %",
                         [{"indicador": "Estudiantes prioritarios", "valor": f"{r.prio} de {r.n} ({r.pct:.1f} %)",
                           "referencia": f"umbral {rr['pct_prioritarios_centro']} %"},
                          {"indicador": "Asistencia media", "valor": f"{r.asis:.1f} %", "referencia": "SQL"},
                          {"indicador": "Promedio medio", "valor": f"{r.prom:.1f}", "referencia": "SQL"}],
                         "alta", r.prio))

    # R-SEG: alertas sin seguimiento
    pend = db.alertas.count_documents({"periodo_codigo": periodo, "vigente": True, "caso_id": None,
                                       "estado": {"$in": ["abierta", "confirmada"]}, "nivel": "prioritario"})
    if pend >= rr["alertas_sin_seguimiento_max"]:
        recs.append(_rec("R-SEG", "global", "TODOS", "Todos los centros", periodo,
                         f"Revisar y asignar responsables a {pend} alertas prioritarias sin caso",
                         "Programar jornada de revisión de alertas con coordinadores de seguimiento.",
                         f"Alertas prioritarias sin caso ≥ {rr['alertas_sin_seguimiento_max']}",
                         [{"indicador": "Alertas prioritarias sin caso abierto", "valor": str(pend),
                           "referencia": f"máximo tolerado {rr['alertas_sin_seguimiento_max']}"}],
                         "alta", pend))

    # R-TEC: centros con necesidad tecnológica alta
    res = tech.resources_frame(conn, periodo, rules)
    if not res.empty:
        for r in res[res["necesidad"] == "alta"].itertuples():
            recs.append(_rec("R-TEC", "centro", r.centro_codigo, r.centro_nombre, periodo,
                             f"Evaluar asignación de equipos y conectividad a {r.centro_nombre}",
                             "Solicitar evaluación técnica para dotación de dispositivos y/o internet.",
                             "Necesidad tecnológica clasificada como alta",
                             [{"indicador": "Internet", "valor": "Sí" if r.tiene_internet else "No",
                               "referencia": "inventario"},
                              {"indicador": "Dispositivos por estudiante", "valor": f"{r.dispositivos_por_estudiante}",
                               "referencia": f"crítico < {rules['tecnologia']['dispositivos_por_estudiante_critico']}"},
                              {"indicador": "Motivos", "valor": r.motivos, "referencia": "criterios F48"}],
                             "media", r.matriculados))

    # R-REG: regiones con brecha de asistencia
    reg, nat = regional.region_table(conn, periodo, rules)
    if not reg.empty:
        for r in reg.itertuples():
            if r.asistencia_pct < nat["asistencia_pct"] - rr["brecha_asistencia_region"]:
                recs.append(_rec("R-REG", "region", r.region_codigo, r.region_nombre, periodo,
                                 f"Estudiar causas de inasistencia en {r.region_nombre}",
                                 "Realizar diagnóstico regional (transporte, contexto familiar, conectividad).",
                                 f"Asistencia regional < nacional − {rr['brecha_asistencia_region']} pts",
                                 [{"indicador": "Asistencia regional", "valor": f"{r.asistencia_pct} %",
                                   "referencia": f"nacional {nat['asistencia_pct']} %"},
                                  {"indicador": "Estudiantes en la muestra", "valor": str(r.estudiantes),
                                   "referencia": "muestra sintética"}],
                                 "media", r.estudiantes))

    # R-CAI: caída de asistencia entre períodos consecutivos
    idx = per.index(periodo)
    if idx > 0:
        prev = indicators.indicator_frame(conn, per[idx - 1])
        a = ind.groupby(["centro_codigo", "centro_nombre"])[["dias_asistidos", "dias_programados"]].sum()
        b = prev.groupby(["centro_codigo", "centro_nombre"])[["dias_asistidos", "dias_programados"]].sum()
        now_pct = a["dias_asistidos"] / a["dias_programados"] * 100
        prev_pct = b["dias_asistidos"] / b["dias_programados"] * 100
        delta = (now_pct - prev_pct).dropna()
        n_by_c = ind.groupby(["centro_codigo", "centro_nombre"]).size()
        for (cod, nom), d in delta[delta <= -rr["caida_asistencia_centro"]].items():
            recs.append(_rec("R-CAI", "centro", cod, nom, periodo,
                             f"Revisar la caída de asistencia en {nom}",
                             "Analizar con la dirección del centro las causas de la caída y medidas preventivas.",
                             f"Caída de asistencia ≥ {rr['caida_asistencia_centro']} pts vs. período anterior",
                             [{"indicador": "Asistencia", "valor": f"{now_pct[(cod, nom)]:.1f} %",
                               "referencia": f"{per[idx - 1]}: {prev_pct[(cod, nom)]:.1f} %"},
                              {"indicador": "Variación", "valor": f"{d:.1f} pts", "referencia": "período anterior"}],
                             "media", n_by_c[(cod, nom)]))

    # F67: priorización transparente = 60 % urgencia + 40 % alcance relativo
    max_alc = max((r["alcance"] for r in recs), default=1) or 1
    for r in recs:
        r["puntaje"] = round(60 * URGENCIA[r["urgencia"]] / 3 + 40 * r["alcance"] / max_alc, 1)
    return sorted(recs, key=lambda r: -r["puntaje"])


def generate(conn: sqlite3.Connection, db: Database, rules: dict, periodo: str | None = None) -> dict:
    """Persiste las recomendaciones en MongoDB `decisiones` de forma idempotente."""
    recs = build(conn, db, rules, periodo)
    now = datetime.now().replace(microsecond=0)
    keys = {r["regla_clave"] for r in recs}
    ops = [UpdateOne({"regla_clave": r["regla_clave"]},
                     {"$set": {**r, "vigente": True, "actualizado_en": now},
                      "$setOnInsert": {"tipo": "recomendacion", "generada_por": "motor_reglas", "generada_en": now,
                                       "estado": "pendiente", "decision": None, "riesgos": [],
                                       "cumplimiento": None, "historial": [
                                           {"fecha": now, "evento": "recomendacion_generada",
                                            "usuario": "motor_reglas", "detalle": r["criterio"]}]}},
                     upsert=True) for r in recs]
    stale = 0
    for d in db.decisiones.find({"estado": "pendiente", "vigente": True}, {"regla_clave": 1}):
        if d["regla_clave"] not in keys and (periodo is None or d["regla_clave"].endswith(periodo)):
            ops.append(UpdateOne({"_id": d["_id"]}, {"$set": {"vigente": False, "actualizado_en": now}}))
            stale += 1
    if ops:
        db.decisiones.bulk_write(ops, ordered=False)
    return {"recomendaciones": len(recs), "sin_vigencia": stale}


def decisions_frame(db: Database, estados=None, solo_vigentes: bool = False) -> pd.DataFrame:
    q: dict = {}
    if estados:
        q["estado"] = {"$in": list(estados)}
    if solo_vigentes:
        q["$or"] = [{"vigente": True}, {"estado": {"$ne": "pendiente"}}]
    docs = list(db.decisiones.find(q).sort([("puntaje", -1)]))
    if not docs:
        return pd.DataFrame()
    df = pd.DataFrame(docs)
    df["objetivo_nombre"] = df["objetivo"].map(lambda o: o.get("nombre"))
    df["responsable"] = df["decision"].map(lambda d: d.get("responsable") if isinstance(d, dict) else None)
    df["fecha_revision"] = df["decision"].map(lambda d: d.get("fecha_revision") if isinstance(d, dict) else None)
    df["riesgo_max"] = df["riesgos"].map(
        lambda rs: max((r["nivel"] for r in rs), key=["bajo", "medio", "alto"].index) if rs else None)
    return df


def register_decision(db: Database, rec_id, accion: str, responsable: str, justificacion: str,
                      fecha_revision: date, riesgos: list[dict], usuario: str, perfil: str | None = None) -> str:
    """F68-F70: decisión humana documentada con responsable, justificación, revisión y riesgos."""
    if accion not in ACCIONES:
        raise ValueError(f"Acción debe ser una de {list(ACCIONES)}")
    if not responsable.strip() or len(justificacion.strip()) < 10:
        raise ValueError("Indique responsable y una justificación (mínimo 10 caracteres).")
    if accion == "aprobar" and not riesgos:
        raise ValueError("Para aprobar debe evaluar al menos un riesgo con su control de mitigación.")
    clean_risks = []
    for r in riesgos:
        p, i = int(r["probabilidad"]), int(r["impacto"])
        if not (1 <= p <= 5 and 1 <= i <= 5):
            raise ValueError("Probabilidad e impacto deben estar entre 1 y 5.")
        if not r.get("descripcion", "").strip() or not r.get("control", "").strip():
            raise ValueError("Cada riesgo requiere descripción y control de mitigación.")
        clean_risks.append({"descripcion": r["descripcion"].strip(), "probabilidad": p, "impacto": i,
                            "puntaje": p * i, "nivel": risk_level(p, i), "control": r["control"].strip(),
                            "riesgo_matriz": r.get("riesgo_matriz")})
    doc = db.decisiones.find_one({"_id": rec_id})
    if not doc:
        raise ValueError("Recomendación inexistente")
    now = datetime.now().replace(microsecond=0)
    estado = ACCIONES[accion]
    decision = {"accion": accion, "responsable": responsable.strip(), "justificacion": justificacion.strip(),
                "fecha_revision": fecha_revision.isoformat() if fecha_revision else None,
                "registrada_por": usuario, "registrada_en": now}
    db.decisiones.update_one({"_id": rec_id}, {
        "$set": {"estado": estado, "decision": decision, "riesgos": clean_risks,
                 "cumplimiento": "no iniciada" if accion == "aprobar" else None},
        "$push": {"historial": {"fecha": now, "evento": f"decision_{accion}", "usuario": usuario,
                                "detalle": justificacion.strip()}}})
    audit.log(usuario, "registrar_decision", "decisiones", str(rec_id),
              {"accion": accion, "responsable": responsable, "riesgos": len(clean_risks)}, perfil)
    return estado


def update_compliance(db: Database, rec_id, cumplimiento: str, nota: str, usuario: str,
                      perfil: str | None = None) -> None:
    """F71: seguimiento del cumplimiento de una decisión aprobada."""
    if cumplimiento not in CUMPLIMIENTO:
        raise ValueError("Estado de cumplimiento inválido")
    doc = db.decisiones.find_one({"_id": rec_id})
    if not doc or doc.get("estado") != "aprobada":
        raise ValueError("Solo las decisiones aprobadas tienen seguimiento de cumplimiento.")
    now = datetime.now().replace(microsecond=0)
    db.decisiones.update_one({"_id": rec_id}, {"$set": {"cumplimiento": cumplimiento}, "$push": {"historial": {
        "fecha": now, "evento": "cumplimiento", "usuario": usuario, "detalle": f"{cumplimiento}. {nota}".strip()}}})
    audit.log(usuario, "actualizar_cumplimiento", "decisiones", str(rec_id), {"cumplimiento": cumplimiento}, perfil)
