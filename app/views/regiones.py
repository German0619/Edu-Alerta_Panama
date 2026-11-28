"""Pantalla 5 · Comparación regional con mapa interactivo (F51-F56)."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common
from common import esc
from edualerta.db import sql
from edualerta.services import regional

u = common.guard("regiones")
conn = common.conn()
rules = sql.get_rules(conn)

common.header("Comparación regional",
              "Dónde se concentran las necesidades y qué regiones conviene estudiar o atender primero.")
f = common.filters_bar(show_grade=False)
if not f["periodo"]:
    st.stop()

METRICAS = {
    "asistencia_pct": "Asistencia %", "aprobacion_pct": "Aprobación %", "promedio": "Promedio",
    "prioritarios_pct": "% prioritarios", "conectividad_pct": "Conectividad %",
    "dispositivos_por_estudiante": "Disp./estudiante", "n_criterios_desfavorables": "Criterios desfavorables",
}
HIGHER_BETTER = {"prioritarios_pct": False, "n_criterios_desfavorables": False}

a, b, c = st.columns([1, 1, 2.2], gap="medium")
zonas = a.multiselect("Zona", ["urbana", "rural"], key="rg_zona", placeholder="Todas")
niveles = b.multiselect("Nivel educativo", ["premedia", "media"], key="rg_niv", placeholder="Todos")
with c:
    metric = st.selectbox("Indicador que colorea el mapa", list(METRICAS), format_func=METRICAS.get,
                          key="rg_metric")
reg, nat = regional.region_table(conn, f["periodo"], rules, zonas or None, f["centros"] or None, niveles or None)
if reg.empty:
    common.empty("Sin datos para estos filtros.")
    st.stop()
reg_view = reg[reg["region_codigo"].isin(f["regiones"])] if f["regiones"] else reg
better_high = HIGHER_BETTER.get(metric, True)
geo = regional.geojson()

left, right = st.columns([1.7, 1], gap="large")
with left:
    selected = None
    if geo is None:
        common.empty("No se encontró la geometría procesada.", "Ejecute el pipeline en Datos y ETL.")
    else:
        kwargs = dict(geojson=geo, locations="region_codigo", featureidkey="properties.codigo", color=metric,
                      hover_name="region_nombre", opacity=0.85,
                      color_continuous_scale=[[0, common.RED], [0.5, "#F1D37A"], [1, common.GREEN]] if better_high
                      else [[0, common.GREEN], [0.5, "#F1D37A"], [1, common.RED]],
                      hover_data={"region_codigo": False, "estudiantes": True, "asistencia_pct": ":.1f",
                                  "aprobacion_pct": ":.1f", "conectividad_pct": ":.1f"},
                      labels={**METRICAS, "estudiantes": "Estudiantes"},
                      center={"lat": 8.62, "lon": -80.15}, zoom=5.95)
        try:
            fig = px.choropleth_map(reg_view, map_style="carto-positron", **kwargs)
        except AttributeError:  # plotly < 5.24
            fig = px.choropleth_mapbox(reg_view, mapbox_style="carto-positron", **kwargs)
        fig.update_traces(marker_line_color="white", marker_line_width=1.5)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                          coloraxis_colorbar=dict(title="", orientation="h", y=0.97, yanchor="top", x=0.03, xanchor="left",
                                                  len=0.5, thickness=8, bgcolor="rgba(255,255,255,.85)"))
        ev = common.chart(fig, 470, on_select="rerun", selection_mode="points", key="rg_map")
        pts = (ev.selection.points if ev and ev.selection else []) or []
        selected = pts[0].get("location") if pts else None
        common.note("Haga clic en una región para ver su detalle. Geometría hexagonal simplificada para la "
                    "demostración; no representa límites oficiales.")
with right:
    names = dict(zip(reg["region_codigo"], reg["region_nombre"]))
    codes = sorted(names, key=names.get)
    if selected in codes:
        st.session_state["rg_sel"] = selected
    if st.session_state.get("rg_sel") not in codes:
        st.session_state["rg_sel"] = reg.sort_values("n_criterios_desfavorables", ascending=False).iloc[0]["region_codigo"]
    sel = st.selectbox("Región", codes, format_func=names.get, key="rg_sel")
    r = reg[reg["region_codigo"] == sel].iloc[0]

    def cmp(key, unit="", higher=True, dec=1):
        v, n = r.get(key), nat.get(key)
        if v is None or n is None:
            return {"k": METRICAS.get(key, key), "v": "—"}
        d = v - n
        return {"k": METRICAS.get(key, key), "v": f"{v:.{dec}f}{unit}",
                "d": f"{d:+.{dec}f} vs. nacional", "good": (d >= 0) == higher if abs(d) > 1e-9 else None}

    common.facts([cmp("asistencia_pct", " %"), cmp("aprobacion_pct", " %"), cmp("promedio"),
                  {"k": "% prioritarios", "v": f"{r['prioritarios_pct']:.1f} %"},
                  cmp("conectividad_pct", " %"), cmp("dispositivos_por_estudiante", "", True, 2)])
    common.note(f"Muestra: {int(r['estudiantes'])} estudiantes en {int(r['centros'])} centros.")
    if not r["muestra_suficiente"]:
        st.warning(f"La muestra tiene menos de {regional.MUESTRA_MINIMA} estudiantes: interprete con cautela.",
                   icon=":material/info:")
    if r["alertas_regionales"]:
        items = "".join(f"<li class='bad'><span>{esc(x)}</span></li>" for x in r["alertas_regionales"].split("; "))
        st.markdown(f"#### Criterios desfavorables<ul class='edu-reasons'>{items}</ul>", unsafe_allow_html=True)
    else:
        common.note("Sin criterios desfavorables frente a la referencia nacional de la muestra.")

# ----------------------------------------------------------------- comparación
st.markdown("### Asistencia por región")
d = reg_view.sort_values("asistencia_pct")
fig = go.Figure()
fig.add_vline(x=nat["asistencia_pct"], line_dash="dot", line_color=common.GREY, line_width=1,
              annotation_text=f"nacional {nat['asistencia_pct']:.1f} %", annotation_position="top",
              annotation_font=dict(size=11, color=common.MUTED))
fig.add_vline(x=nat["asistencia_pct"] - rules["recomendaciones"]["brecha_asistencia_region"], line_dash="dot",
              line_color=common.RED, line_width=1, annotation_text="umbral de brecha", annotation_position="top",
              annotation_font=dict(size=11, color=common.RED))
colors = [common.RED if n >= 2 else common.AMBER if n == 1 else common.GREEN for n in d["n_criterios_desfavorables"]]
fig.add_scatter(x=d["asistencia_pct"], y=d["region_nombre"], mode="markers+text",
                marker=dict(size=13, color=colors, line=dict(color="white", width=1.5)),
                text=[f"{v:.1f}" for v in d["asistencia_pct"]], textposition="middle right",
                textfont=dict(size=11, color=common.MUTED), hovertemplate="%{y}: %{x:.1f} %<extra></extra>",
                showlegend=False)
lo = min(d["asistencia_pct"].min(), nat["asistencia_pct"] - 4) - 1
fig.update_xaxes(range=[lo, 100], title="Asistencia %")
fig.update_yaxes(title="")
fig.update_layout(margin=dict(l=4, r=12, t=30, b=4))
common.chart(fig, max(320, 28 * len(d) + 80))
common.note("Color del punto: verde sin criterios desfavorables, ámbar uno, rojo dos o más.")

st.markdown("### Tablero regional")
cols = {k: METRICAS[k] for k in ("asistencia_pct", "aprobacion_pct", "promedio", "prioritarios_pct",
                                 "conectividad_pct", "dispositivos_por_estudiante")}
nat_ref = {**nat, "prioritarios_pct": reg["prioritarios"].sum() / reg["estudiantes"].sum() * 100}
heat = reg_view.sort_values("n_criterios_desfavorables", ascending=False).copy()
heat["estudiantes_txt"] = heat["estudiantes"]
common.heat_table(heat, {**cols, "estudiantes": "Estudiantes"}, {**nat_ref, "estudiantes": None}, "region_nombre",
                  "Región", HIGHER_BETTER,
                  {"dispositivos_por_estudiante": "{:.2f}", "estudiantes": "{:.0f}"})
common.note("Verde: mejor que la referencia nacional de la muestra; rojo: peor. La intensidad indica la distancia. "
            "Los datos son sintéticos y las conclusiones, demostrativas.")
common.csv_button(common.pretty(reg_view), f"comparacion_regional_{f['periodo']}.csv")

st.markdown(f"### Evolución de {names[sel]}")
tr = regional.region_trend(conn, sel)
if not tr.empty:
    long = tr.melt(id_vars="periodo_codigo", value_vars=["asistencia_pct", "aprobacion_pct", "prioritarios_pct"],
                   var_name="indicador", value_name="valor")
    long["indicador"] = long["indicador"].map(METRICAS)
    fig = px.line(long, x="periodo_codigo", y="valor", color="indicador", markers=True,
                  labels={"valor": "%", "periodo_codigo": "", "indicador": ""})
    fig.update_traces(line_width=3, marker_size=9)
    common.chart(fig, 300)
