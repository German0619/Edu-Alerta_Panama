"""Flujo demostrativo completo del caso E-0042 (sección 9 del catálogo, F36-F44, F65-F71, F75)."""
from datetime import date

import pytest

from edualerta.db import sql
from edualerta.etl import pipeline
from edualerta.services import alerts, audit, followup, kpi, recommendations


def test_flujo_completo_e0042(fresh):
    c, db = fresh["conn"], fresh["db"]
    aid = "E-0042|2025-T3"

    # 3-4. alerta prioritaria generada -> la coordinadora la confirma
    with pytest.raises(ValueError):
        followup.open_case(db, aid, "Tutor", "tutor", None, "alison")           # aún no confirmada
    with pytest.raises(ValueError):
        alerts.review_alert(db, aid, "confirmar", "", "alison")                 # motivo obligatorio
    alerts.review_alert(db, aid, "confirmar", "Ausencias verificadas con el docente guía", "alison", "seguimiento")
    caso_id = followup.open_case(db, aid, "Prof. Méndez", "tutor", date(2026, 1, 15), "alison", "seguimiento")
    assert db.alertas.find_one({"_id": aid})["caso_id"] == caso_id

    # 5. tutoría registrada en MongoDB
    followup.add_intervention(db, caso_id, "tutoría", date(2025, 12, 1), "Tutoría académica de matemáticas",
                              date(2026, 3, 15), "alison", observacion="Muestra interés al trabajar en grupo.",
                              perfil="seguimiento")
    caso = db.casos.find_one({"_id": caso_id})
    assert caso["estado"] == "en seguimiento" and caso["n_intervenciones"] == 1
    assert db.observaciones.find_one({"caso_id": caso_id})

    # 6. el dashboard refleja el nuevo estado del caso
    rules = sql.get_rules(c)
    k = kpi.compute(c, db, "2025-T3", rules)
    assert k["intervenciones_realizadas"]["valor"] == 100.0
    assert k["alertas_sin_seguimiento"]["valor"] == db.alertas.count_documents(
        {"periodo_codigo": "2025-T3", "vigente": True}) - 1

    # nueva carga 2026-T1 -> evolución posterior
    staged = pipeline.stage_demo_package()
    assert len(staged) == 4
    out = pipeline.run(trigger="test")
    assert out["rechazados"] >= 2                                               # fecha 2026-02-30 y nota -5
    evo = followup.evolution(c, caso)
    after = evo[evo["momento"] == "después"].iloc[0]
    assert after["periodo_codigo"] == "2026-T1"
    assert after["Δ asistencia"] == 16.0 and after["Δ promedio"] == 10.0
    assert after["nivel_alerta"] == "preventivo"

    perfil = followup.student_profile(c, db, "E-0042")
    assert len(perfil["indicadores"]) == 4 and not perfil["linea_tiempo"].empty

    # 7. la dirección decide sobre una recomendación y evalúa riesgos
    df = recommendations.decisions_frame(db, estados=["pendiente"])
    assert not df.empty and (df["generada_por"] == "motor_reglas").all()
    rec_id = df.iloc[0]["_id"]
    with pytest.raises(ValueError):
        recommendations.register_decision(db, rec_id, "aprobar", "Dirección", "Justificación suficiente", None,
                                          [], "nathalia")                      # aprobar exige riesgos
    estado = recommendations.register_decision(
        db, rec_id, "aprobar", "Coordinación académica", "La evidencia muestra concentración de casos",
        date(2026, 4, 1), [{"descripcion": "Clasificación errónea", "probabilidad": 3, "impacto": 5,
                            "control": "Revisión humana", "riesgo_matriz": "R2"}], "nathalia", "direccion")
    assert estado == "aprobada"
    d = db.decisiones.find_one({"_id": rec_id})
    assert d["decision"]["registrada_por"] == "nathalia" and d["riesgos"][0]["nivel"] == "alto"
    recommendations.update_compliance(db, rec_id, "en curso", "Tutores asignados", "nathalia")
    assert db.decisiones.find_one({"_id": rec_id})["cumplimiento"] == "en curso"

    # auditoría: quién, qué y cuándo
    ev = audit.events()
    for accion in ("alerta_confirmada", "abrir_caso", "registrar_intervencion", "registrar_decision",
                   "ejecutar_pipeline"):
        assert accion in set(ev["accion"]), accion


def test_descartar_alerta_y_reapertura(fresh):
    db = fresh["db"]
    al = db.alertas.find_one({"nivel": "preventivo", "periodo_codigo": "2025-T3"})
    alerts.review_alert(db, al["_id"], "descartar", "Ausencias por cita médica documentada", "alison")
    assert db.alertas.find_one({"_id": al["_id"]})["estado"] == "descartada"
    with pytest.raises(ValueError):
        followup.open_case(db, al["_id"], "X", "tutor", None, "alison")


def test_case_cannot_close_without_intervention(fresh):
    db = fresh["db"]
    aid = db.alertas.find_one({"nivel": "prioritario", "_id": {"$ne": "E-0042|2025-T3"}})["_id"]
    alerts.review_alert(db, aid, "confirmar", "Verificado con el docente", "alison")
    cid = followup.open_case(db, aid, "Orientadora Ruiz", "orientador", None, "alison")
    with pytest.raises(ValueError):
        followup.update_case_status(db, cid, "cerrado", "Sin motivo real", "alison")
