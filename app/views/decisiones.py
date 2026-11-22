"""Pantalla 7 · Decisiones y recomendaciones gerenciales (F65-F71)."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import common
from common import esc
from edualerta import config
from edualerta.db import sql
from edualerta.services import recommendations as recs

u = common.guard("decisiones")
conn, db = common.conn(), common.require_db()
can_decide = common.can("registrar_decision")

common.header("Decisiones gerenciales",
              "El sistema recomienda con reglas explícitas; una persona responsable decide, justifica y evalúa "
              "los riesgos.")

REGLAS = {"R-TUT": "Tutorías en centro", "R-SEG": "Alertas sin caso", "R-TEC": "Tecnología",
          "R-REG": "Brecha regional", "R-CAI": "Caída de asistencia"}
ESTADO_COLORS = {"pendiente": common.GREY, "aprobada": common.GREEN, "pospuesta": common.AMBER,
                 "rechazada": common.RED, "en revisión": common.COBALT}
RIESGO_COLORS = {"bajo": common.GREEN, "medio": common.AMBER, "alto": common.RED}

df = recs.decisions_frame(db)
pend_all = df[df["estado"].isin(["pendiente", "pospuesta", "en revisión"]) & df["vigente"]] if not df.empty else df
dec_all = df[df["estado"] != "pendiente"] if not df.empty else df
common.kpi_band([
    {"label": "Esperan decisión", "value": len(pend_all)},
    {"label": "Aprobadas", "value": int((df["estado"] == "aprobada").sum()) if not df.empty else 0},
    {"label": "Pospuestas o en revisión",
     "value": int(df["estado"].isin(["pospuesta", "en revisión"]).sum()) if not df.empty else 0},
    {"label": "Rechazadas", "value": int((df["estado"] == "rechazada").sum()) if not df.empty else 0},
])

t1, t2 = st.tabs(["Por decidir", "Decisiones registradas"])

with t1:
    a, b = st.columns([3, 1], vertical_alignment="bottom")
    tipos = a.pills("Tipo de recomendación", list(REGLAS), format_func=REGLAS.get, selection_mode="multi",
                    key="rec_tipos")
    with b:
        if st.button("Recalcular", icon=":material/refresh:", use_container_width=True,
                     help="Vuelve a aplicar las reglas con los datos y umbrales actuales."):
            out = recs.generate(conn, db, sql.get_rules(conn))
            st.toast(f"{out['recomendaciones']} recomendaciones vigentes.")
            st.rerun()
    pend = pend_all[pend_all["regla"].isin(tipos)] if tipos and not pend_all.empty else pend_all
    if pend.empty:
        common.empty("No hay recomendaciones esperando decisión.",
                      "Se generan automáticamente cada vez que se ejecuta el pipeline.")
    else:
        pend = pend.reset_index(drop=True)
        view = pend.assign(tipo=pend["regla"].map(REGLAS))
        common.note(f"{len(pend)} recomendaciones. Prioridad = 60 % urgencia + 40 % estudiantes afectados. "
                    "Seleccione una para ver la evidencia y decidir.")
        ev = common.table(view, ["puntaje", "urgencia", "tipo", "titulo", "alcance", "estado"],
                          rename={"tipo": "Tipo", "estado": "Estado"}, max_height=330, on_select="rerun",
                          selection_mode="single-row", key="rec_tab",
                          column_config={"Prioridad": st.column_config.ProgressColumn(
                              min_value=0, max_value=100, format="%.0f", width="small"),
                              "Recomendación": st.column_config.TextColumn(width="large")})
        if ev.selection.rows:
            st.session_state["rec_sel"] = str(pend.iloc[ev.selection.rows[0]]["_id"])
        if st.session_state.get("rec_sel") not in set(pend["_id"].astype(str)):
            st.session_state["rec_sel"] = str(pend.iloc[0]["_id"])
        doc = pend[pend["_id"].astype(str) == st.session_state["rec_sel"]].iloc[0]

        st.divider()
        common.title_with_chips(doc["titulo"], [
            common.chip(f"prioridad {doc['puntaje']:.0f}", common.SLATE),
            common.chip(f"urgencia {doc['urgencia']}", common.RED if doc["urgencia"] == "alta" else common.AMBER),
            common.soft_chip("recomendación automática")])
        l, r = st.columns([1, 1.15], gap="large")
        with l:
            st.markdown(f"{esc(doc['descripcion'])}")
            common.facts([{"k": "Regla", "v": REGLAS.get(doc["regla"], doc["regla"])},
                          {"k": "Período", "v": doc["periodo_codigo"]},
                          {"k": "Estudiantes afectados", "v": int(doc["alcance"])}])
            st.markdown("#### Evidencia")
            rows = "".join(f"<li><span><b>{esc(e['indicador'])}:</b> {esc(e['valor'])} "
                           f"<span class='edu-note'>({esc(e['referencia'])})</span></span></li>"
                           for e in doc["evidencias"])
            st.markdown(f"<ul class='edu-reasons'>{rows}</ul>", unsafe_allow_html=True)
            common.note(f"Criterio que la activó: {esc(doc['criterio'])}.")
        with r:
            st.markdown("#### Registrar decisión")
            if not can_decide:
                common.empty("Solo el perfil Dirección registra decisiones.", "Usted puede consultar la evidencia.")
            else:
                sel = st.session_state["rec_sel"]
                a, b = st.columns(2)
                acc = a.selectbox("Decisión", list(recs.ACCIONES), format_func=lambda x: x.replace("_", " "),
                                  key=f"acc_{sel}")
                fr = b.date_input("Fecha de revisión", date.today() + timedelta(days=30), key=f"fr_{sel}",
                                  format="DD/MM/YYYY")
                resp = st.text_input("Responsable de ejecución", key=f"resp_{sel}",
                                     placeholder="Persona o unidad que ejecutará la acción")
                just = st.text_area("Justificación", key=f"just_{sel}", height=90,
                                    placeholder="Por qué se toma esta decisión, con base en la evidencia.")
                matrix = config.risk_matrix()
                labels = {m["id"]: f"{m['id']} · {m['riesgo']}" for m in matrix}
                st.markdown("**Riesgos de la decisión**")
                n_risks = st.segmented_control("Cuántos riesgos evaluará", [1, 2, 3, 4], default=1,
                                               key=f"nr_{sel}") or 1
                risks = []
                for i in range(int(n_risks)):
                    with st.container(border=True):
                        base = st.selectbox(f"Riesgo {i + 1}", ["OTRO"] + list(labels), key=f"rb{i}_{sel}",
                                            format_func=lambda k: "Otro (describir)" if k == "OTRO" else labels[k])
                        ref = next((m for m in matrix if m["id"] == base), None)
                        desc = st.text_input("Descripción", ref["riesgo"] if ref else "", key=f"rd{i}_{base}_{sel}")
                        x, y, z = st.columns([1, 1, 2.2])
                        p = x.number_input("Probabilidad", 1, 5, value=ref["probabilidad"] if ref else 3,
                                           help="De 1 (muy baja) a 5 (muy alta).", key=f"rp{i}_{base}_{sel}")
                        im = y.number_input("Impacto", 1, 5, value=ref["impacto"] if ref else 3,
                                            help="De 1 (mínimo) a 5 (grave).", key=f"ri{i}_{base}_{sel}")
                        ctl = z.text_input("Control de mitigación", ref["preventivo"] if ref else "",
                                           key=f"rc{i}_{base}_{sel}")
                        lvl = recs.risk_level(p, im)
                        st.markdown(f"{common.chip('riesgo ' + lvl, RIESGO_COLORS[lvl])} "
                                    f"<span class='edu-note'>{p} × {im} = {p * im}</span>", unsafe_allow_html=True)
                        risks.append({"descripcion": desc, "probabilidad": p, "impacto": im, "control": ctl,
                                      "riesgo_matriz": ref["id"] if ref else None})
                if st.button("Registrar decisión", type="primary", use_container_width=True):
                    try:
                        estado = recs.register_decision(db, doc["_id"], acc, resp, just, fr, risks, u["usuario"],
                                                        u["perfil"])
                        st.toast(f"Decisión registrada: {estado}.")
                        st.session_state.pop("rec_sel", None)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                common.note("Nivel de riesgo = probabilidad × impacto: bajo (menos de 8), medio (8 a 14), "
                            "alto (15 o más).")

with t2:
    if dec_all.empty:
        common.empty("Aún no se han registrado decisiones.",
                     "Las decisiones se registran desde la pestaña «Por decidir».")
    else:
        dec = dec_all.reset_index(drop=True).copy()
        dec["fecha_revision"] = dec["fecha_revision"].map(common.fmt_date)
        evd = common.table(dec, ["titulo", "estado", "responsable", "fecha_revision", "cumplimiento", "riesgo_max",
                                 "periodo_codigo"], rename={"estado": "Decisión"},
                           color_cols={"Decisión": ESTADO_COLORS, "Riesgo máx.": RIESGO_COLORS},
                           on_select="rerun", selection_mode="single-row", key="dec_tab")
        common.csv_button(common.pretty(dec[["titulo", "estado", "responsable", "fecha_revision", "cumplimiento",
                                             "riesgo_max", "periodo_codigo"]]), "historial_decisiones.csv")
        if evd.selection.rows:
            st.session_state["dec_sel"] = str(dec.iloc[evd.selection.rows[0]]["_id"])
        if st.session_state.get("dec_sel") not in set(dec["_id"].astype(str)):
            st.session_state["dec_sel"] = str(dec.iloc[0]["_id"])
        d = dec[dec["_id"].astype(str) == st.session_state["dec_sel"]].iloc[0]
        dd = d["decision"] or {}
        st.divider()
        common.title_with_chips(d["titulo"], [common.chip(d["estado"], ESTADO_COLORS.get(d["estado"], common.GREY)),
                                              common.soft_chip("decisión humana")])
        l, r = st.columns([1.2, 1], gap="large")
        with l:
            common.facts([{"k": "Decidió", "v": dd.get("registrada_por", "—")},
                          {"k": "Responsable", "v": dd.get("responsable", "—")},
                          {"k": "Revisión", "v": common.fmt_date(dd.get("fecha_revision"))},
                          {"k": "Cumplimiento", "v": d["cumplimiento"] or "no aplica"}])
            st.markdown(f"**Justificación.** {esc(dd.get('justificacion', '—'))}")
            if d["riesgos"]:
                st.markdown("#### Riesgos evaluados")
                rk = pd.DataFrame(d["riesgos"])
                common.table(rk, ["descripcion", "probabilidad", "impacto", "nivel", "control"],
                             rename={"nivel": "Riesgo"}, color_cols={"Riesgo": RIESGO_COLORS})
        with r:
            if d["estado"] == "aprobada":
                with st.form("cumpl"):
                    st.markdown("#### Seguimiento del cumplimiento")
                    a, b = st.columns([1, 1.4])
                    cu = a.selectbox("Estado", recs.CUMPLIMIENTO,
                                     index=recs.CUMPLIMIENTO.index(d["cumplimiento"] or "no iniciada"))
                    nota = b.text_input("Nota")
                    if st.form_submit_button("Actualizar cumplimiento",
                                             disabled=not (can_decide or common.can("gestionar_caso"))):
                        try:
                            recs.update_compliance(db, d["_id"], cu, nota, u["usuario"], u["perfil"])
                            st.toast("Cumplimiento actualizado.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
            st.markdown("#### Historial")
            common.timeline([{"when": h["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(h["fecha"], "strftime")
                              else str(h["fecha"]), "what": h["evento"].replace("_", " "), "txt": h.get("detalle"),
                              "who": h.get("usuario")} for h in reversed(d["historial"])])
