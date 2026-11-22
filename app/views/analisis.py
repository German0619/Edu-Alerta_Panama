"""Pantalla 6 · Análisis: tendencias, comparaciones y ficha de KPI (F31, F35, F58-F60, F62-F64)."""
import pandas as pd
import plotly.express as px
import streamlit as st

import common
from edualerta import config
from edualerta.db import sql
from edualerta.services import indicators, kpi, regional, segmentation, tech

u = common.guard("analisis")
conn = common.conn()
rules = sql.get_rules(conn)

common.header("Análisis", "Tendencias entre períodos y cruces entre rendimiento, tecnología y región.")
f = common.filters_bar()
if not f["periodo"]:
    st.stop()

NAMES = {"asistencia_pct": "Asistencia", "aprobacion_pct": "Aprobación", "conectividad_pct": "Conectividad",
         "prioritarios": "prioritario", "preventivos": "preventivo"}

t1, t2, t3, t5, t4 = st.tabs(["Tendencias", "Comparar períodos", "Cruces por centro", "Perfiles de centros",
                              "Ficha de cada KPI"])

with t1:
    tr = kpi.trend(conn, rules, f["regiones"], f["centros"], f["grados"])
    if tr.empty:
        common.empty("Sin datos para estos filtros.")
    else:
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown("#### Indicadores por período")
            long = tr.melt(id_vars="periodo_codigo", value_vars=["asistencia_pct", "aprobacion_pct", "conectividad_pct"],
                           var_name="ind", value_name="valor")
            long["ind"] = long["ind"].map(NAMES)
            fig = px.line(long, x="periodo_codigo", y="valor", color="ind", markers=True,
                          labels={"valor": "%", "periodo_codigo": "", "ind": ""})
            fig.update_traces(line_width=3, marker_size=9)
            common.chart(fig, 320)
        with b:
            st.markdown("#### Estudiantes con señales de riesgo")
            long = tr.melt(id_vars="periodo_codigo", value_vars=["prioritarios", "preventivos"], var_name="nivel",
                           value_name="n_estudiantes")
            long["nivel"] = long["nivel"].map(NAMES)
            fig = px.bar(long, x="periodo_codigo", y="n_estudiantes", color="nivel",
                         color_discrete_map=common.NIVEL_COLORS, barmode="group", text="n_estudiantes",
                         labels={"periodo_codigo": "", "n_estudiantes": "Estudiantes", "nivel": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            common.chart(fig, 320)
        common.table(tr.drop(columns=["anio", "trimestre"]),
                     rename={"periodo_codigo": "Período"})
        common.csv_button(common.pretty(tr.drop(columns=["anio", "trimestre"])), "tendencias.csv")
        sa = indicators.subject_averages(conn, centros=f["centros"] or None)
        if not sa.empty:
            st.markdown("#### Promedio por asignatura")
            piv = sa.pivot_table(index="asignatura", columns="periodo_codigo", values="nota").round(1)
            per_cols = list(piv.columns)
            piv["Variación"] = (piv[per_cols[-1]] - piv[per_cols[0]]).round(1) if len(per_cols) > 1 else 0
            piv = piv.sort_values(per_cols[-1]).reset_index()
            fig = px.bar(sa, x="nota", y="asignatura", color="periodo_codigo", barmode="group", orientation="h",
                         labels={"nota": "Promedio", "asignatura": "", "periodo_codigo": ""},
                         category_orders={"asignatura": list(piv["asignatura"])},
                         color_discrete_sequence=["#B9CBE3", "#6E97C9", common.COBALT, common.SLATE])
            lo = max(0, sa["nota"].min() - 5)
            fig.update_xaxes(range=[lo, min(100, sa["nota"].max() + 2)])
            common.chart(fig, 340)
            common.note(f"Eje horizontal desde {lo:.0f} para que se aprecien las diferencias.")

with t2:
    per = sql.periods(conn)
    a, b, _ = st.columns([1, 1, 2])
    p0 = a.selectbox("Período base", per, index=max(0, per.index(f["periodo"]) - 1))
    p1 = b.selectbox("Comparar con", per, index=per.index(f["periodo"]))
    i0 = indicators.indicator_frame(conn, p0, f["regiones"], f["centros"], f["grados"])
    i1 = indicators.indicator_frame(conn, p1, f["regiones"], f["centros"], f["grados"])
    if p0 == p1:
        common.empty("Elija dos períodos distintos para comparar.", "Por ejemplo, el trimestre anterior como base.")
    elif i0.empty or i1.empty:
        common.empty("Sin datos para alguno de los períodos.")
    else:
        k0 = kpi.compute(conn, None, p0, rules, f["regiones"], f["centros"], f["grados"])
        k1 = kpi.compute(conn, None, p1, rules, f["regiones"], f["centros"], f["grados"])
        items = []
        for key in ["tasa_asistencia", "tasa_aprobacion", "conectividad_escolar", "disponibilidad_dispositivos"]:
            v0, v1 = k0[key]["valor"], k1[key]["valor"]
            d = None if v0 is None or v1 is None else v1 - v0
            items.append({"label": k1[key]["nombre"], "value": "—" if v1 is None else
                          (f"{v1:.1f}" if k1[key]["unidad"] == "%" else f"{v1:.2f}"),
                          "unit": "%" if k1[key]["unidad"] == "%" else "",
                          "delta": None if d is None else f"{d:+.2f} vs. {p0}", "good": None if not d else d > 0})
        common.kpi_band(items)
        merged = i0[["estudiante_codigo", "asistencia_pct", "promedio", "nivel_alerta"]].merge(
            i1[["estudiante_codigo", "centro_codigo", "asistencia_pct", "promedio", "nivel_alerta"]],
            on="estudiante_codigo", suffixes=("_0", "_1"))
        l, r = st.columns([1, 1.3], gap="large")
        with l:
            st.markdown(f"#### Cambio de nivel {p0} → {p1}")
            order = ["prioritario", "preventivo", "regular"]
            trans = pd.crosstab(merged["nivel_alerta_0"], merged["nivel_alerta_1"]).reindex(
                index=order, columns=order, fill_value=0)
            fig = px.imshow(trans, text_auto=True, color_continuous_scale=["#F4F7F5", "#9FB9D9", common.COBALT],
                            labels={"x": f"Nivel en {p1}", "y": f"Nivel en {p0}", "color": "Estudiantes"})
            fig.update_layout(coloraxis_showscale=False)
            fig.update_traces(textfont=dict(size=15))
            common.chart(fig, 330)
            common.note("Lectura: fila = nivel en el período base; columna = nivel en el período comparado. "
                        "Debajo de la diagonal, estudiantes que mejoraron.")
        with r:
            st.markdown("#### Estudiantes con mayor deterioro")
            merged["d_asis"] = (merged["asistencia_pct_1"] - merged["asistencia_pct_0"]).round(1)
            merged["d_prom"] = (merged["promedio_1"] - merged["promedio_0"]).round(1)
            worst = merged.sort_values("d_asis").head(12)
            common.table(worst, ["estudiante_codigo", "centro_codigo", "asistencia_pct_0", "asistencia_pct_1",
                                 "d_asis", "d_prom", "nivel_alerta_1"],
                         rename={"asistencia_pct_0": f"Asist. {p0}", "asistencia_pct_1": f"Asist. {p1}",
                                 "d_asis": "Δ asistencia", "d_prom": "Δ promedio", "nivel_alerta_1": "Nivel"})
        common.csv_button(common.pretty(merged), f"comparacion_{p0}_{p1}.csv")

with t3:
    ind = indicators.indicator_frame(conn, f["periodo"], f["regiones"], f["centros"], f["grados"])
    res = tech.resources_frame(conn, f["periodo"], rules, f["regiones"] or None)
    if ind.empty:
        common.empty("Sin datos para estos filtros.")
    else:
        byc = ind.groupby(["centro_codigo", "centro_nombre", "region_nombre", "zona"]).agg(
            estudiantes=("estudiante_codigo", "count"), dias_asistidos=("dias_asistidos", "sum"),
            dias_programados=("dias_programados", "sum"), promedio=("promedio", "mean"),
            prioritarios=("nivel_alerta", lambda s: (s == "prioritario").sum())).reset_index()
        byc["asistencia_pct"] = (byc["dias_asistidos"] / byc["dias_programados"] * 100).round(1)
        byc["prioritarios_pct"] = (byc["prioritarios"] / byc["estudiantes"] * 100).round(1)
        byc["promedio"] = byc["promedio"].round(1)
        byc["centro"] = byc["centro_nombre"].str.replace("Centro Educativo ", "", regex=False)
        if not res.empty:
            byc = byc.merge(res[["centro_codigo", "dispositivos_por_estudiante", "tiene_internet", "necesidad"]],
                            on="centro_codigo", how="left")
            l, r = st.columns([1.6, 1], gap="large")
            with l:
                st.markdown("#### Tecnología frente a asistencia")
                fig = px.scatter(byc, x="dispositivos_por_estudiante", y="asistencia_pct", size="estudiantes",
                                 color="prioritarios_pct", symbol="zona", hover_name="centro", size_max=20,
                                 color_continuous_scale=["#F4E3C2", common.AMBER, common.RED],
                                 labels={"dispositivos_por_estudiante": "Dispositivos por estudiante",
                                         "asistencia_pct": "Asistencia %", "prioritarios_pct": "% prioritarios",
                                         "zona": "Zona"})
                fig.update_traces(marker=dict(line=dict(color="white", width=1)))
                fig.update_layout(coloraxis_colorbar=dict(title="% prior.", len=.6))
                common.chart(fig, 400)
            with r:
                st.markdown("#### Correlación entre indicadores")
                corr = byc[["asistencia_pct", "promedio", "prioritarios_pct", "dispositivos_por_estudiante"]].corr()
                lab = ["Asistencia", "Promedio", "% prior.", "Disp./est."]
                fig = px.imshow(corr.values, x=lab, y=lab, text_auto=".2f", zmin=-1, zmax=1,
                                color_continuous_scale=[common.RED, "#F4F7F5", common.COBALT])
                fig.update_layout(coloraxis_showscale=False)
                common.chart(fig, 330)
                common.note("Descriptiva, por centro. Una correlación no demuestra causalidad.")
        common.table(byc, ["centro_codigo", "centro", "region_nombre", "zona", "estudiantes", "asistencia_pct",
                           "promedio", "prioritarios_pct"] + (["dispositivos_por_estudiante", "necesidad"]
                                                              if "necesidad" in byc else []),
                     rename={"centro": "Centro educativo"})
        common.csv_button(common.pretty(byc), f"comparacion_centros_{f['periodo']}.csv")

with t5:
    st.markdown("Agrupa los centros con necesidades parecidas para diseñar intervenciones por tipo de perfil, en "
                "lugar de una misma respuesta para todos.")
    feats = segmentation.center_features(conn, f["periodo"], rules)
    if len(feats) < 6:
        common.empty("No hay suficientes centros con datos para segmentar en este período.")
    else:
        seg = segmentation.segment(feats)
        common.kpi_band([
            {"label": "Centros analizados", "value": len(feats)},
            {"label": "Grupos encontrados", "value": seg["k"],
             "help": "Se prueban de 2 a 5 grupos y se elige el de mayor coeficiente de silueta."},
            {"label": "Coeficiente de silueta", "value": f"{seg['silueta']:.2f}",
             "delta": "separación entre grupos (de −1 a 1)",
             "help": "Mayor a 0.25 indica grupos razonablemente diferenciados."},
        ])
        palette = [common.RED, common.AMBER, common.COBALT, "#3E8E7E", "#8A5A9E"]
        cols = st.columns(len(seg["grupos"]), gap="medium")
        for col, g in zip(cols, seg["grupos"]):
            with col:
                color = palette[(g["grupo"] - 1) % len(palette)]
                st.markdown(f"<div style='border-top:4px solid {color};padding-top:.6rem'>"
                            f"<div class='edu-note'>Grupo {g['grupo']}</div>"
                            f"<h4 style='margin:.1rem 0 .3rem'>{common.esc(g['perfil'])}</h4>"
                            f"<div class='edu-note'>{g['centros']} centros · {g['estudiantes']} estudiantes</div></div>",
                            unsafe_allow_html=True)
                rasgos = "".join(
                    f"<li class='{'bad' if t == 'peor' else ''}'><span>{'Menor' if (t == 'peor') == (n != 'estudiantes prioritarios') else 'Mayor'} "
                    f"{common.esc(n)} que el promedio</span></li>" for t, n, _ in g["rasgos"]) or                     "<li><span>Cerca del promedio en todo</span></li>"
                st.markdown(f"<ul class='edu-reasons'>{rasgos}</ul>", unsafe_allow_html=True)
                common.facts([{"k": "Asistencia", "v": f"{g['asistencia_pct']:.1f} %"},
                              {"k": "Prioritarios", "v": f"{g['prioritarios_pct']:.1f} %"},
                              {"k": "Disp./est.", "v": f"{g['dispositivos_por_estudiante']:.2f}"},
                              {"k": "Con internet", "v": f"{g['tiene_internet'] * 100:.0f} %"}])
        cen = seg["centros"].copy()
        cen[["asistencia_pct", "promedio", "prioritarios_pct"]] = cen[["asistencia_pct", "promedio",
                                                                       "prioritarios_pct"]].round(1)
        cen["dispositivos_por_estudiante"] = cen["dispositivos_por_estudiante"].round(2)
        cen["grupo_txt"] = cen["grupo"].map(lambda g: f"Grupo {g}")
        cen["centro"] = cen["centro_nombre"].str.replace("Centro Educativo ", "", regex=False)
        fig = px.scatter(cen, x="dispositivos_por_estudiante", y="asistencia_pct", color="grupo_txt",
                         size="estudiantes", hover_name="centro", size_max=20,
                         color_discrete_sequence=palette,
                         category_orders={"grupo_txt": [f"Grupo {g['grupo']}" for g in seg["grupos"]]},
                         hover_data={"region_nombre": True, "prioritarios_pct": ":.1f", "grupo_txt": False},
                         labels={"dispositivos_por_estudiante": "Dispositivos por estudiante",
                                 "asistencia_pct": "Asistencia %", "grupo_txt": "", "region_nombre": "Región",
                                 "prioritarios_pct": "% prioritarios"})
        fig.update_traces(marker=dict(line=dict(color="white", width=1)))
        common.chart(fig, 380)
        common.table(cen.sort_values(["grupo", "prioritarios_pct"], ascending=[True, False]),
                     ["grupo", "centro_codigo", "centro", "region_nombre", "zona", "asistencia_pct", "promedio",
                      "prioritarios_pct", "dispositivos_por_estudiante"],
                     rename={"grupo": "Grupo", "centro": "Centro educativo"})
        common.csv_button(common.pretty(cen.drop(columns=["grupo_txt"])), f"perfiles_centros_{f['periodo']}.csv")
        common.note("Técnica: k-means sobre indicadores estandarizados (asistencia, promedio, % prioritarios, "
                    "dispositivos por estudiante y conectividad), inicialización k-means++ con semilla fija y número de "
                    f"grupos elegido por silueta (probados: {', '.join(f'k={k}: {v}' for k, v in seg['silueta_por_k'].items())}). "
                    "Con datos sintéticos los grupos son demostrativos y orientan, no reemplazan, la decisión.")

with t4:
    common.note("Cada indicador declara su fórmula, fuente, periodicidad, filtros y responsable de interpretación. "
                "Ninguno se escribe a mano: se recalculan con cada ejecución del pipeline.")
    cat = config.kpi_catalog()
    vals = kpi.compute(conn, common.db(), f["periodo"], rules, f["regiones"], f["centros"], f["grados"])
    for key, d in cat.items():
        v = vals[key]
        val = "sin dato" if v["valor"] is None else f"{v['valor']} {d['unidad']}"
        with st.expander(f"{d['nombre']}: {val}"):
            common.facts([{"k": "Cálculo actual", "v": f"{v['numerador']} / {v['denominador']}"},
                          {"k": "Periodicidad", "v": d["periodicidad"].split(" (")[0]},
                          {"k": "Responsable", "v": d["responsable"].split(" (")[0]}])
            st.markdown(f"{d['descripcion']}\n\n**Fórmula:** {d['formula']}  \n**Fuente:** {d['fuente']}  \n"
                        f"**Filtros aplicables:** {', '.join(d['filtros'])}")
    common.note("En la tasa de asistencia, las ausencias justificadas se excluyen de los días programados para no "
                "penalizar inasistencias documentadas.")
