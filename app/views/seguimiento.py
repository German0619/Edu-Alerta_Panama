"""Pantalla 3 · Seguimiento: alertas, revisión, casos e intervenciones (F28, F33-F44)."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
from common import esc
from edualerta.db import sql
from edualerta.services import alerts, followup

u = common.guard("seguimiento")
conn, db = common.conn(), common.require_db()
f = common.sidebar_filters()
can_review = common.can("revisar_alerta")
can_case = common.can("gestionar_caso")

common.header("Seguimiento académico",
              "Revise cada alerta, confirme los casos reales, asigne responsable y registre las intervenciones.")
if not f["periodo"]:
    st.stop()

t_al, t_ca, t_pe = st.tabs(["Alertas", "Casos e intervenciones", "Perfil del estudiante"])

EVENT_COLORS = {"generada": common.GREY, "confirmada": common.COBALT, "descartada": "#B0B8B4",
                "caso_abierto": common.SLATE, "nivel_actualizado": common.AMBER, "reabierta": common.RED}


def reasons_html(motivos) -> str:
    items = "".join(f"<li>{common.nivel_chip(m['nivel'])}<span>{esc(m['texto'])}</span></li>" for m in motivos)
    return f'<ul class="edu-reasons">{items or "<li>Sin motivos</li>"}</ul>'


# =================================================================== ALERTAS (F33-F38)
with t_al:
    allp = alerts.alerts_frame(db, f["periodo"], centros=f["centros"] or None, regiones=f["regiones"] or None)
    common.kpi_band([
        {"label": "Alertas vigentes", "value": len(allp)},
        {"label": "Prioritarias", "value": int((allp["nivel"] == "prioritario").sum()) if not allp.empty else 0},
        {"label": "Pendientes de revisión", "value": int((allp["estado"] == "abierta").sum()) if not allp.empty else 0},
        {"label": "Con caso abierto", "value": int(allp["caso_id"].notna().sum()) if not allp.empty else 0},
    ])
    a, b, c = st.columns([1, 1.25, 1], gap="medium")
    niveles = a.pills("Nivel", ["prioritario", "preventivo"], selection_mode="multi",
                      default=["prioritario", "preventivo"], key="al_niv")
    estados = b.pills("Estado de revisión", ["abierta", "confirmada", "descartada"], selection_mode="multi",
                      default=["abierta", "confirmada"], key="al_est")
    buscar = c.text_input("Buscar estudiante", placeholder="Código, p. ej. E-0042", key="al_q").strip().upper()
    df = alerts.alerts_frame(db, f["periodo"], niveles or None, estados or None, f["centros"] or None,
                             f["regiones"] or None)
    if f["grados"] and not df.empty:
        df = df[df["grado"].isin(f["grados"])]
    if buscar and not df.empty:
        df = df[df["estudiante_codigo"].str.contains(buscar, regex=False)]

    if df.empty:
        common.empty("No hay alertas con estos filtros.", "Pruebe a incluir otros niveles o estados de revisión.")
    else:
        view = df[["_id", "estudiante_codigo", "centro_codigo", "grado", "nivel", "estado", "asistencia_pct",
                   "promedio", "max_ausencias_consecutivas", "caso_id"]].copy()
        view["motivos"] = df["motivos"].map(lambda ms: "; ".join(m["texto"] for m in ms))
        view["nivel"] = view["nivel"].astype(str)
        common.note(f"{len(view)} {'alerta' if len(view) == 1 else 'alertas'}. Seleccione una fila para revisarla.")
        ev = common.table(view, [c for c in view.columns if c != "_id"], max_height=360, on_select="rerun",
                          selection_mode="single-row", key="al_tab",
                          column_config={"Motivos": st.column_config.TextColumn(width="large")})
        rows = ev.selection.rows
        if rows:
            st.session_state["al_sel"] = view.iloc[rows[0]]["_id"]
        sel_id = st.session_state.get("al_sel")
        if sel_id in set(view["_id"]):  # la selección se conserva tras registrar una acción
            al = db.alertas.find_one({"_id": sel_id})
            st.divider()
            common.title_with_chips(f"{al['estudiante_codigo']} · {al['periodo_codigo']}",
                                    [common.nivel_chip(al["nivel"]),
                                     common.chip(al["estado"], common.ESTADO_ALERTA_COLORS[al["estado"]])])
            i = al["indicadores"]
            l, r = st.columns([1.25, 1], gap="large")
            with l:
                common.facts([
                    {"k": "Asistencia", "v": f"{i['asistencia_pct']:.1f} %" if i.get("asistencia_pct") is not None else "—"},
                    {"k": "Promedio", "v": f"{i['promedio']:.1f}" if i.get("promedio") is not None else "—"},
                    {"k": "Ausencias consecutivas", "v": int(i.get("max_ausencias_consecutivas") or 0)},
                    {"k": "Ausencias justificadas", "v": int(i.get("ausencias_justificadas") or 0),
                     "d": "no cuentan para la alerta"},
                    {"k": "Episodios de ausencia", "v": int(i.get("episodios_ausencia") or 0),
                     "d": "ausencias recurrentes"},
                    {"k": "Asignaturas reprobadas", "v": int(i.get("asignaturas_reprobadas") or 0)},
                    {"k": "Centro y grado", "v": f"{al['centro_codigo']} · {al['grado']}.º"},
                ])
                st.markdown("#### Motivos de la alerta")
                st.markdown(reasons_html(al["motivos"]), unsafe_allow_html=True)
                common.note("La alerta es una señal, no un diagnóstico. Antes de confirmar, verifique ausencias "
                            "justificadas, la calidad del dato y el contexto del estudiante.")
                with st.expander("Historial de la alerta"):
                    common.timeline([{"when": h["fecha"].strftime("%d/%m/%Y %H:%M") if hasattr(h["fecha"], "strftime")
                                      else str(h["fecha"]), "what": h["evento"].replace("_", " "),
                                      "txt": h.get("detalle"), "who": h.get("usuario"),
                                      "color": EVENT_COLORS.get(h["evento"], common.COBALT)}
                                     for h in reversed(al.get("historial", []))])
                if st.button("Abrir perfil del estudiante", icon=":material/person_search:"):
                    st.session_state["pe_code"] = al["estudiante_codigo"]
                    st.toast("Perfil listo en la pestaña «Perfil del estudiante».")
            with r:
                reviewed = al["estado"] in ("confirmada", "descartada")
                common.step(1, "Revisión humana", "Confirme o descarte con una justificación.",
                            "done" if reviewed else "")
                if not al.get("caso_id"):
                    with st.form(f"rev_{al['_id']}"):
                        acc = st.radio("Decisión", ["confirmar", "descartar"], horizontal=True,
                                       index=0 if al["estado"] != "descartada" else 1)
                        mot = st.text_area("Justificación", placeholder="Ej.: El docente guía verificó que las "
                                                                        "ausencias no están justificadas.")
                        label = "Actualizar revisión" if reviewed else "Registrar revisión"
                        if st.form_submit_button(label, type="primary", disabled=not can_review):
                            try:
                                alerts.review_alert(db, al["_id"], acc, mot, u["usuario"], u["perfil"])
                                st.toast("Revisión registrada.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                elif al.get("revision"):
                    common.note(f"Confirmada por <b>{esc(al['revision']['usuario'])}</b>: "
                                f"{esc(al['revision']['motivo'])}")
                common.step(2, "Caso de seguimiento", "Se abre solo desde una alerta confirmada.",
                            "done" if al.get("caso_id") else ("" if al["estado"] == "confirmada" else "off"))
                if al["estado"] == "confirmada" and not al.get("caso_id"):
                    with st.form(f"case_{al['_id']}"):
                        resp = st.text_input("Responsable", placeholder="Nombre del tutor u orientador")
                        a2, b2 = st.columns(2)
                        rol = a2.selectbox("Rol", followup.ROLES_RESPONSABLE)
                        prox = b2.date_input("Próxima revisión", date.today() + timedelta(days=14),
                                             format="DD/MM/YYYY")
                        if st.form_submit_button("Abrir caso", type="primary", disabled=not can_case):
                            try:
                                cid = followup.open_case(db, al["_id"], resp, rol, prox, u["usuario"], u["perfil"])
                                st.toast(f"Caso {cid} abierto.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                if al.get("caso_id"):
                    common.note(f"Caso <b>{esc(al['caso_id'])}</b>. Registre las intervenciones en la pestaña "
                                "«Casos e intervenciones».")
                if not can_review:
                    common.note("Su perfil puede consultar alertas, pero no revisarlas.")
        common.csv_button(common.pretty(view.drop(columns=["_id"])), f"alertas_{f['periodo']}.csv")

# =================================================================== CASOS (F37-F44)
with t_ca:
    est_f = st.pills("Estado del caso", followup.ESTADOS_CASO, selection_mode="multi",
                     default=["pendiente", "en seguimiento", "atendido"], key="ca_est")
    cases = followup.cases_frame(db, est_f or None, f["centros"] or None)
    if cases.empty:
        common.empty("No hay casos con estos filtros.",
                     "Los casos se abren en la pestaña «Alertas», después de confirmar una alerta.")
    else:
        cview = cases.copy()
        for col in ("ultima_intervencion", "proxima_revision", "abierto_en"):
            cview[col] = cview[col].map(common.fmt_date)
        cev = common.table(cview, ["_id", "estudiante_codigo", "centro_codigo", "nivel", "responsable",
                                   "rol_responsable", "estado", "n_intervenciones", "ultima_intervencion",
                                   "proxima_revision"],
                           rename={"_id": "Caso", "estado": "Estado del caso"}, max_height=300,
                           on_select="rerun", selection_mode="single-row", key="ca_tab")
        if cev.selection.rows:
            st.session_state["ca_sel"] = cases.iloc[cev.selection.rows[0]]["_id"]
        if len(cases) == 1:
            st.session_state.setdefault("ca_sel", cases.iloc[0]["_id"])
        if st.session_state.get("ca_sel") in set(cases["_id"]):
            caso = db.casos.find_one({"_id": st.session_state["ca_sel"]})
            st.divider()
            common.title_with_chips(f"Caso de {caso['estudiante_codigo']}",
                                    [common.nivel_chip(caso["nivel"]),
                                     common.chip(caso["estado"], common.CASO_COLORS[caso["estado"]])])
            common.facts([
                {"k": "Responsable", "v": caso["responsable"], "d": caso["rol_responsable"]},
                {"k": "Centro", "v": caso["centro_codigo"]},
                {"k": "Intervenciones", "v": caso.get("n_intervenciones", 0)},
                {"k": "Próxima revisión", "v": common.fmt_date(caso.get("proxima_revision"))},
            ])
            l, r = st.columns([1.25, 1], gap="large")
            with l:
                st.markdown("#### Evolución antes y después")
                evo = followup.evolution(conn, caso)
                if evo.empty:
                    common.note("Sin indicadores para comparar.")
                else:
                    rules = sql.get_rules(conn)["alertas"]["prioritario"]
                    fig = go.Figure()
                    fig.add_scatter(x=evo["periodo_codigo"], y=evo["asistencia_pct"], name="Asistencia %",
                                    mode="lines+markers", line=dict(color=common.COBALT, width=3),
                                    marker=dict(size=9))
                    fig.add_scatter(x=evo["periodo_codigo"], y=evo["promedio"], name="Promedio",
                                    mode="lines+markers", line=dict(color="#3E8E7E", width=3), marker=dict(size=9))
                    fig.add_hline(y=rules["asistencia_min"], line_dash="dot", line_color=common.RED, line_width=1,
                                  annotation_text=f"umbral asistencia {rules['asistencia_min']}",
                                  annotation_position="top left", annotation_font=dict(size=11, color=common.RED))
                    fig.add_hline(y=rules["promedio_min"], line_dash="dot", line_color=common.AMBER, line_width=1,
                                  annotation_text=f"umbral promedio {rules['promedio_min']}",
                                  annotation_position="bottom left", annotation_font=dict(size=11, color=common.AMBER))
                    fig.add_vline(x=caso["periodo_codigo"], line_dash="dash", line_color=common.GREY, line_width=1)
                    fig.update_yaxes(range=[40, 100])
                    common.chart(fig, 300)
                    after = evo[evo["momento"] == "después"]
                    if not after.empty:
                        last = after.iloc[-1]
                        common.facts([
                            {"k": f"Asistencia {last['periodo_codigo']}", "v": f"{last['asistencia_pct']:.1f} %",
                             "d": f"{last['Δ asistencia']:+.1f} pts", "good": last["Δ asistencia"] >= 0},
                            {"k": f"Promedio {last['periodo_codigo']}", "v": f"{last['promedio']:.1f}",
                             "d": f"{last['Δ promedio']:+.1f} pts", "good": last["Δ promedio"] >= 0},
                            {"k": "Nivel actual", "v": last["nivel_alerta"]},
                        ])
                    else:
                        common.note("Todavía no hay un período posterior al de la alerta. Cuando se cargue "
                                    "(p. ej., el paquete 2026-T1 en Datos y ETL) aquí se verá el efecto.")
                st.markdown("#### Historial del caso")
                ints = list(db.intervenciones.find({"caso_id": caso["_id"]}).sort("fecha", -1))
                hist = [{"when": common.fmt_date(x["fecha"]), "what": f"Intervención: {x['tipo']}",
                         "txt": x["descripcion"], "who": f"{x['responsable']} · registró {x['registrado_por']}",
                         "color": common.COBALT} for x in ints]
                hist += [{"when": h["fecha"].strftime("%d/%m/%Y") if hasattr(h["fecha"], "strftime") else str(h["fecha"]),
                          "what": h["evento"].replace("_", " "), "txt": h.get("detalle"), "who": h.get("usuario"),
                          "color": common.SLATE} for h in reversed(caso.get("historial", []))
                         if h["evento"] != "intervencion"]
                common.timeline(hist)
            with r:
                if caso["estado"] != "cerrado":
                    st.markdown("#### Registrar intervención")
                    with st.form(f"int_{caso['_id']}", clear_on_submit=True):
                        a2, b2 = st.columns(2)
                        tipo = a2.selectbox("Tipo", followup.TIPOS_INTERVENCION)
                        fecha = b2.date_input("Fecha", date.today(), format="DD/MM/YYYY")
                        desc = st.text_area("Acción realizada", placeholder="Ej.: Tutoría de matemáticas, "
                                                                            "2 sesiones por semana.")
                        obs = st.text_area("Observación cualitativa", height=80,
                                           placeholder="Lo que se observó durante la intervención (opcional).")
                        a2, b2 = st.columns(2)
                        prox = a2.date_input("Próxima revisión", date.today() + timedelta(days=14),
                                             format="DD/MM/YYYY")
                        nuevo = b2.selectbox("Estado del caso", ["(automático)"] + followup.ESTADOS_CASO[1:3])
                        if st.form_submit_button("Guardar intervención", type="primary", disabled=not can_case):
                            try:
                                followup.add_intervention(db, caso["_id"], tipo, fecha, desc, prox, u["usuario"],
                                                          None if nuevo == "(automático)" else nuevo, obs, u["perfil"])
                                st.toast("Intervención guardada.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                st.markdown("#### Cambiar estado del caso")
                with st.form(f"st_{caso['_id']}"):
                    a2, b2 = st.columns([1.15, 1])
                    nuevo = a2.selectbox("Nuevo estado", followup.ESTADOS_CASO,
                                         index=followup.ESTADOS_CASO.index(caso["estado"]))
                    mot = b2.text_input("Motivo", placeholder="Obligatorio para cerrar")
                    if st.form_submit_button("Cambiar estado", disabled=not can_case):
                        try:
                            followup.update_case_status(db, caso["_id"], nuevo, mot, u["usuario"], u["perfil"])
                            st.toast("Estado actualizado.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
        common.csv_button(common.pretty(cview), "casos_seguimiento.csv")

# =================================================================== PERFIL (F26, F28, F35, F40)
with t_pe:
    a, _ = st.columns([1, 2.5])
    code = a.text_input("Código del estudiante", value=st.session_state.get("pe_code", "E-0042"),
                        key="pe_input").strip().upper()
    exists = conn.execute("SELECT 1 FROM estudiantes WHERE codigo=?", (code,)).fetchone()
    if not exists:
        common.empty("No existe un estudiante con ese código.", "Use el formato E-NNNN, por ejemplo E-0042.")
        st.stop()
    prof = followup.student_profile(conn, db, code)
    info = prof["info"]
    valid = info.dropna(subset=["periodo_codigo"])
    last = valid.iloc[-1] if not valid.empty else None
    ind = prof["indicadores"]
    chips = [common.nivel_chip(ind.iloc[-1]["nivel_alerta"])] if not ind.empty else []
    common.title_with_chips(code, chips)
    if last is not None:
        common.note(f"{esc(last['centro'])} · {esc(last['region'])} · {int(last['grado'])}.º grado · "
                    f"género {esc(info.iloc[0]['genero'])}, nacido en {info.iloc[0]['anio_nacimiento']}. "
                    "Registro sintético sin nombres ni documentos de identidad.")
    l, r = st.columns([1.25, 1], gap="large")
    with l:
        st.markdown("#### Indicadores por período")
        if ind.empty:
            common.note("Sin indicadores.")
        else:
            fig = go.Figure()
            fig.add_bar(x=ind["periodo_codigo"], y=ind["asistencia_pct"], name="Asistencia %",
                        marker_color=[common.NIVEL_COLORS[n] for n in ind["nivel_alerta"]], width=0.5,
                        text=[f"{v:.0f} %" for v in ind["asistencia_pct"]], textposition="inside",
                        insidetextfont=dict(color="white"))
            fig.add_scatter(x=ind["periodo_codigo"], y=ind["promedio"], name="Promedio", mode="lines+markers",
                            line=dict(color=common.SLATE, width=3), marker=dict(size=9))
            fig.update_yaxes(range=[0, 100])
            common.chart(fig, 290)
            common.note("El color de cada barra indica el nivel de riesgo del período.")
            common.table(ind, ["periodo_codigo", "asistencia_pct", "promedio", "max_ausencias_consecutivas",
                               "ausencias_justificadas", "asignaturas_reprobadas", "nivel_alerta"])
        notas = prof["notas"]
        if not notas.empty:
            st.markdown("#### Calificaciones por asignatura")
            pv = notas.pivot_table(index="asignatura", columns="periodo_codigo", values="nota").reset_index()
            common.table(pv.rename(columns={"asignatura": "Asignatura"}))
    with r:
        st.markdown("#### Historial de seguimiento")
        tl = prof["linea_tiempo"]
        if tl.empty:
            common.note("Sin registros de seguimiento.")
        else:
            rows = []
            for t in tl.sort_values("fecha", ascending=False).head(14).to_dict("records"):
                color = (common.COBALT if t["tipo"].startswith("Intervención") else
                         common.SLATE if t["tipo"].startswith("Caso") else
                         common.AMBER if t["tipo"].startswith("Alerta") else "#3E8E7E")
                rows.append({"when": common.fmt_date(t["fecha"]), "what": t["tipo"], "txt": t["detalle"],
                             "who": t.get("autor"), "color": color})
            common.timeline(rows)
            if len(tl) > 14:
                common.note(f"Se muestran los 14 registros más recientes de {len(tl)}.")
        with st.form("obs_new", clear_on_submit=True):
            st.markdown("#### Nueva observación")
            tipo = st.selectbox("Tipo", followup.TIPOS_OBSERVACION, format_func=common.term)
            txt = st.text_area("Texto", height=80)
            if st.form_submit_button("Guardar observación", disabled=not common.can("registrar_observacion")):
                try:
                    followup.add_observation(db, code, txt, tipo, u["usuario"], perfil=u["perfil"])
                    st.toast("Observación guardada.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        own = [o for o in prof["observaciones"] if o.get("origen") == "aplicacion"]
        if own and common.can("registrar_observacion"):
            with st.expander("Corregir una observación registrada"):
                opts = {str(o["_id"]): f"{common.fmt_date(o['fecha'])} · {o['texto'][:50]}" for o in own}
                oid = st.selectbox("Observación", list(opts), format_func=opts.get)
                cur = next(o for o in own if str(o["_id"]) == oid)
                new = st.text_area("Texto corregido", cur["texto"], key=f"ed_{oid}")
                if st.button("Guardar corrección"):
                    followup.update_observation(db, oid, new, u["usuario"], u["perfil"])
                    st.toast("Observación corregida.")
                    st.rerun()
