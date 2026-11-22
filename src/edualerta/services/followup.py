"""Seguimiento de casos e intervenciones (F37-F44) y consulta integrada SQL + MongoDB (F26-F28)."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pandas as pd
from pymongo.database import Database

from edualerta.db import sql
from edualerta.services import audit

ROLES_RESPONSABLE = ["tutor", "orientador", "coordinador"]
TIPOS_INTERVENCION = ["tutoría", "entrevista", "contacto familiar", "apoyo académico", "otra"]
ESTADOS_CASO = ["pendiente", "en seguimiento", "atendido", "cerrado"]
TIPOS_OBSERVACION = ["observacion", "diagnostico", "intervencion"]


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _iso(d) -> str | None:
    if d is None:
        return None
    return d.isoformat() if isinstance(d, (date, datetime)) else str(d)


def open_case(db: Database, alerta_id: str, responsable: str, rol: str, proxima_revision: date | None,
              usuario: str, perfil: str | None = None) -> str:
    """F37-F38: abre un caso a partir de una alerta CONFIRMADA y asigna responsable."""
    if rol not in ROLES_RESPONSABLE:
        raise ValueError(f"Rol debe ser uno de {ROLES_RESPONSABLE}")
    if not responsable.strip():
        raise ValueError("Debe indicar el nombre del responsable.")
    alerta = db.alertas.find_one({"_id": alerta_id})
    if not alerta:
        raise ValueError("Alerta inexistente")
    if alerta["estado"] != "confirmada":
        raise ValueError("Solo se puede abrir un caso a partir de una alerta confirmada.")
    if alerta.get("caso_id"):
        raise ValueError(f"La alerta ya tiene el caso {alerta['caso_id']}.")
    now = _now()
    caso_id = "CASO-" + alerta_id.replace("|", "-")
    db.casos.insert_one({
        "_id": caso_id, "alerta_id": alerta_id, "estudiante_codigo": alerta["estudiante_codigo"],
        "periodo_codigo": alerta["periodo_codigo"], "centro_codigo": alerta["centro_codigo"],
        "region_codigo": alerta.get("region_codigo"), "nivel": alerta["nivel"],
        "motivos": [m["texto"] for m in alerta.get("motivos", [])],
        "responsable": responsable.strip(), "rol_responsable": rol, "estado": "pendiente",
        "abierto_en": now, "abierto_por": usuario, "proxima_revision": _iso(proxima_revision),
        "n_intervenciones": 0, "ultima_intervencion": None,
        "historial": [{"fecha": now, "evento": "caso_abierto", "usuario": usuario,
                       "detalle": f"Responsable: {responsable.strip()} ({rol})"}],
    })
    db.alertas.update_one({"_id": alerta_id}, {"$set": {"caso_id": caso_id}, "$push": {"historial": {
        "fecha": now, "evento": "caso_abierto", "usuario": usuario, "detalle": caso_id}}})
    audit.log(usuario, "abrir_caso", "casos", caso_id, {"alerta": alerta_id, "responsable": responsable, "rol": rol},
              perfil)
    return caso_id


def add_intervention(db: Database, caso_id: str, tipo: str, fecha: date, descripcion: str,
                     proxima_revision: date | None, usuario: str, nuevo_estado: str | None = None,
                     observacion: str | None = None, perfil: str | None = None) -> str:
    """F39-F42: registra la intervención, la observación cualitativa y actualiza el estado del caso."""
    if tipo not in TIPOS_INTERVENCION:
        raise ValueError(f"Tipo debe ser uno de {TIPOS_INTERVENCION}")
    if not descripcion or len(descripcion.strip()) < 5:
        raise ValueError("Describa la intervención realizada.")
    fecha_d = date.fromisoformat(_iso(fecha)[:10]) if fecha else date.today()
    if fecha_d > date.today():
        raise ValueError("La fecha de la intervención no puede ser futura: registre acciones ya realizadas.")
    if proxima_revision and date.fromisoformat(_iso(proxima_revision)[:10]) < fecha_d:
        raise ValueError("La próxima revisión no puede ser anterior a la fecha de la intervención.")
    caso = db.casos.find_one({"_id": caso_id})
    if not caso:
        raise ValueError("Caso inexistente")
    if caso["estado"] == "cerrado":
        raise ValueError("El caso está cerrado.")
    estado = nuevo_estado or ("en seguimiento" if caso["estado"] == "pendiente" else caso["estado"])
    if estado not in ESTADOS_CASO:
        raise ValueError("Estado de caso inválido")
    now = _now()
    res = db.intervenciones.insert_one({
        "caso_id": caso_id, "estudiante_codigo": caso["estudiante_codigo"], "centro_codigo": caso["centro_codigo"],
        "periodo_codigo": caso["periodo_codigo"], "tipo": tipo, "fecha": _iso(fecha_d),
        "descripcion": descripcion.strip(), "responsable": caso["responsable"],
        "rol_responsable": caso["rol_responsable"], "proxima_revision": _iso(proxima_revision),
        "estado_caso_resultante": estado, "registrado_por": usuario, "registrado_en": now,
    })
    if observacion and observacion.strip():
        add_observation(db, caso["estudiante_codigo"], observacion, "intervencion", usuario, caso_id=caso_id,
                        perfil=perfil, fecha=fecha)
    # Las intervenciones pueden registrarse en otro orden (p. ej., retroactivas): la última es la de fecha mayor.
    ultima = max(filter(None, [caso.get("ultima_intervencion"), _iso(fecha_d)]))
    db.casos.update_one({"_id": caso_id}, {
        "$set": {"estado": estado, "proxima_revision": _iso(proxima_revision), "ultima_intervencion": ultima},
        "$inc": {"n_intervenciones": 1},
        "$push": {"historial": {"fecha": now, "evento": "intervencion", "usuario": usuario,
                                "detalle": f"{tipo}: {descripcion.strip()[:80]} · estado {estado}"}}})
    audit.log(usuario, "registrar_intervencion", "intervenciones", str(res.inserted_id),
              {"caso": caso_id, "tipo": tipo, "estado": estado}, perfil)
    return str(res.inserted_id)


def update_case_status(db: Database, caso_id: str, estado: str, motivo: str, usuario: str,
                       perfil: str | None = None) -> None:
    """F42."""
    if estado not in ESTADOS_CASO:
        raise ValueError("Estado de caso inválido")
    caso = db.casos.find_one({"_id": caso_id})
    if not caso:
        raise ValueError("Caso inexistente")
    if estado == "cerrado" and (not motivo or len(motivo.strip()) < 5):
        raise ValueError("Para cerrar el caso documente el motivo.")
    if estado in ("atendido", "cerrado") and caso.get("n_intervenciones", 0) == 0:
        raise ValueError("No se puede marcar como atendido/cerrado un caso sin intervenciones registradas.")
    now = _now()
    db.casos.update_one({"_id": caso_id}, {"$set": {"estado": estado}, "$push": {"historial": {
        "fecha": now, "evento": "cambio_estado", "usuario": usuario,
        "detalle": f"{caso['estado']} → {estado}. {motivo or ''}".strip()}}})
    audit.log(usuario, "cambiar_estado_caso", "casos", caso_id, {"de": caso["estado"], "a": estado,
                                                                 "motivo": motivo}, perfil)


def add_observation(db: Database, estudiante: str, texto: str, tipo: str, usuario: str, caso_id: str | None = None,
                    perfil: str | None = None, fecha: date | None = None) -> str:
    """F26 (crear) / F40: observación cualitativa en MongoDB vinculada por el código anónimo."""
    if tipo not in TIPOS_OBSERVACION:
        raise ValueError("Tipo de observación inválido")
    if not texto or len(texto.strip()) < 5:
        raise ValueError("La observación está vacía.")
    res = db.observaciones.insert_one({
        "estudiante_codigo": estudiante, "fecha": _iso(fecha or date.today()), "tipo": tipo,
        "texto": texto.strip(), "autor_rol": perfil or "seguimiento", "autor": usuario, "caso_id": caso_id,
        "origen": "aplicacion", "registrado_en": _now()})
    audit.log(usuario, "registrar_observacion", "observaciones", str(res.inserted_id),
              {"estudiante": estudiante, "tipo": tipo}, perfil)
    return str(res.inserted_id)


def update_observation(db: Database, obs_id, texto: str, usuario: str, perfil: str | None = None) -> None:
    """F26 (actualizar)."""
    from bson import ObjectId
    if not texto or not texto.strip():
        raise ValueError("La observación está vacía.")
    key = ObjectId(obs_id) if ObjectId.is_valid(str(obs_id)) else obs_id
    actual = db.observaciones.find_one({"_id": key}, {"texto": 1})
    if not actual:
        raise ValueError("Observación inexistente")
    now = _now()
    # Se conserva la versión anterior: una corrección no debe borrar la evidencia original (F75).
    db.observaciones.update_one({"_id": key}, {
        "$set": {"texto": texto.strip(), "editado_por": usuario, "editado_en": now},
        "$push": {"versiones": {"texto": actual["texto"], "reemplazado_en": now, "reemplazado_por": usuario}}})
    audit.log(usuario, "editar_observacion", "observaciones", str(obs_id),
              {"antes": actual["texto"], "despues": texto.strip()}, perfil)


def cases_frame(db: Database, estados=None, centros=None, periodo: str | None = None, regiones=None,
                grados=None) -> pd.DataFrame:
    """Casos filtrados con el mismo alcance que los KPI (período, región, centro y grado de la alerta)."""
    q: dict = {}
    if estados:
        q["estado"] = {"$in": list(estados)}
    if centros:
        q["centro_codigo"] = {"$in": list(centros)}
    if regiones:
        q["region_codigo"] = {"$in": list(regiones)}
    if periodo:
        q["periodo_codigo"] = periodo
    if grados:  # el grado está en la alerta que originó el caso
        q["alerta_id"] = {"$in": [a["_id"] for a in db.alertas.find({"grado": {"$in": [int(g) for g in grados]}},
                                                                    {"_id": 1})]}
    docs = list(db.casos.find(q, {"historial": 0}).sort("abierto_en", -1))
    cols = ["_id", "estudiante_codigo", "periodo_codigo", "centro_codigo", "nivel", "responsable", "rol_responsable",
            "estado", "n_intervenciones", "ultima_intervencion", "proxima_revision", "abierto_en"]
    return pd.DataFrame(docs, columns=cols) if docs else pd.DataFrame(columns=cols)


def student_profile(conn: sqlite3.Connection, db: Database, estudiante: str) -> dict:
    """F28: perfil integrado - indicadores cuantitativos (SQL) + historial cualitativo (MongoDB)."""
    info = sql.query_df(conn, """
        SELECT e.codigo, e.genero, e.anio_nacimiento, m.periodo_codigo, m.grado, m.estado,
               c.codigo AS centro_codigo, c.nombre AS centro, r.nombre AS region
        FROM estudiantes e
        LEFT JOIN matriculas m ON m.estudiante_codigo=e.codigo
        LEFT JOIN centros c ON c.codigo=m.centro_codigo
        LEFT JOIN regiones r ON r.codigo=c.region_codigo
        LEFT JOIN periodos p ON p.codigo=m.periodo_codigo
        WHERE e.codigo=? ORDER BY p.anio, p.trimestre""", (estudiante,))
    ind = sql.query_df(conn, """SELECT i.* FROM indicadores i JOIN periodos p ON p.codigo=i.periodo_codigo
                                WHERE estudiante_codigo=? ORDER BY p.anio, p.trimestre""", (estudiante,))
    notas = sql.query_df(conn, "SELECT periodo_codigo, asignatura, nota FROM calificaciones WHERE estudiante_codigo=?",
                         (estudiante,))
    alertas = list(db.alertas.find({"estudiante_codigo": estudiante}).sort("periodo_codigo", 1))
    casos = list(db.casos.find({"estudiante_codigo": estudiante}).sort("abierto_en", 1))
    intervenciones = list(db.intervenciones.find({"estudiante_codigo": estudiante}).sort("fecha", 1))
    observaciones = list(db.observaciones.find({"estudiante_codigo": estudiante}).sort("fecha", 1))

    def _ts(v) -> str:
        return v.isoformat() if isinstance(v, (date, datetime)) else str(v or "")

    # `fecha` es el día que se muestra; `orden` añade la hora de registro para que los eventos del mismo día
    # queden en orden cronológico real (F43).
    timeline = []
    for o in observaciones:
        timeline.append({"fecha": str(o["fecha"])[:10], "orden": f"{str(o['fecha'])[:10]} {_ts(o.get('registrado_en'))}",
                         "tipo": f"Observación · {o['tipo']}",
                         "detalle": o["texto"], "autor": o.get("autor") or o.get("autor_rol"),
                         "origen": o.get("origen", "")})
    for i in intervenciones:
        timeline.append({"fecha": str(i["fecha"])[:10], "orden": f"{str(i['fecha'])[:10]} {_ts(i.get('registrado_en'))}",
                         "tipo": f"Intervención · {i['tipo']}",
                         "detalle": i["descripcion"], "autor": i["registrado_por"], "origen": i["caso_id"]})
    for a in alertas:
        for h in a.get("historial", []):
            timeline.append({"fecha": str(h["fecha"])[:10], "orden": f"{str(h['fecha'])[:10]} {_ts(h['fecha'])}",
                             "tipo": f"Alerta {a['periodo_codigo']} · {h['evento']}",
                             "detalle": h.get("detalle", ""), "autor": h.get("usuario"), "origen": a["_id"]})
    for c in casos:
        for h in c.get("historial", []):
            if h["evento"] != "intervencion":
                timeline.append({"fecha": str(h["fecha"])[:10], "orden": f"{str(h['fecha'])[:10]} {_ts(h['fecha'])}",
                                 "tipo": f"Caso · {h['evento']}",
                                 "detalle": h.get("detalle", ""), "autor": h.get("usuario"), "origen": c["_id"]})
    timeline.sort(key=lambda t: t["orden"])
    return {"info": info, "indicadores": ind, "notas": notas, "alertas": alertas, "casos": casos,
            "intervenciones": intervenciones, "observaciones": observaciones,
            "linea_tiempo": pd.DataFrame(timeline)}


def evolution(conn: sqlite3.Connection, caso: dict) -> pd.DataFrame:
    """F44: compara los indicadores del período de la alerta (antes) con los períodos posteriores."""
    df = sql.query_df(conn, """SELECT i.periodo_codigo, i.asistencia_pct, i.promedio, i.max_ausencias_consecutivas,
                                      i.nivel_alerta, p.anio, p.trimestre
                               FROM indicadores i JOIN periodos p ON p.codigo=i.periodo_codigo
                               WHERE i.estudiante_codigo=? ORDER BY p.anio, p.trimestre""",
                      (caso["estudiante_codigo"],))
    if df.empty:
        return df
    base = df[df["periodo_codigo"] == caso["periodo_codigo"]]
    if base.empty:
        return df
    b = base.iloc[0]
    df["momento"] = ["antes" if (r.anio, r.trimestre) < (b.anio, b.trimestre) else
                     "alerta (base)" if r.periodo_codigo == b.periodo_codigo else "después"
                     for r in df.itertuples()]
    df["Δ asistencia"] = (df["asistencia_pct"] - b["asistencia_pct"]).round(1)
    df["Δ promedio"] = (df["promedio"] - b["promedio"]).round(1)
    return df.drop(columns=["anio", "trimestre"])
