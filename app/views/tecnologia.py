"""Pantalla 4 · Recursos tecnológicos escolares (F45-F50)."""
import plotly.express as px
import streamlit as st

import common
from edualerta.db import sql
from edualerta.services import tech

u = common.guard("tecnologia")
conn = common.conn()
rules = sql.get_rules(conn)

common.header("Tecnología escolar",
              "Qué centros carecen de conectividad o dispositivos y cuáles conviene evaluar primero.")
f = common.filters_bar(show_grade=False)
if not f["periodo"]:
    st.stop()


def inventory_form(default_period: str | None = None) -> None:
    """F45-F46: registro/actualización del inventario de un centro y período."""
    if not common.can("editar_recursos"):
        common.empty("Solo el perfil Tecnología registra inventario.", "Usted puede consultar los datos.")
        return
    opts_all = dict(sql.query_df(conn, "SELECT codigo, codigo || ' ' || replace(nombre, 'Centro Educativo ', '') "
                                       "AS n FROM centros ORDER BY codigo").values.tolist())
    periods = sql.all_periods(conn)[::-1]
    a, b = st.columns(2)
    cen = a.selectbox("Centro", list(opts_all), format_func=opts_all.get)
    per = b.selectbox("Período", periods,
                      index=periods.index(default_period) if default_period in periods else 0)
    cur = sql.query_df(conn, "SELECT * FROM recursos_tecnologicos WHERE centro_codigo=? AND periodo_codigo=?",
                       (cen, per))
    cur = cur.iloc[0] if not cur.empty else None
    with st.form(f"rec_{cen}_{per}"):
        a, b = st.columns(2)
        net = a.toggle("Tiene internet", bool(cur["tiene_internet"]) if cur is not None else False)
        vel = b.number_input("Velocidad (Mbps)", 0.0, 1000.0,
                             float(cur["velocidad_mbps"]) if cur is not None else 0.0)
        comp = a.number_input("Computadoras funcionales", 0, 5000,
                              int(cur["computadoras_funcionales"]) if cur is not None else 0)
        tab = b.number_input("Tabletas funcionales", 0, 5000,
                             int(cur["tabletas_funcionales"]) if cur is not None else 0)
        if st.form_submit_button("Guardar inventario", type="primary"):
            try:
                tech.save_resources(conn, cen, per, net, vel, comp, tab, u["usuario"], u["perfil"])
                st.toast("Inventario guardado. Los indicadores ya lo reflejan.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    common.note("Los valores precargados son los registrados para ese centro y período. Cada cambio queda en la "
                "auditoría." if cur is not None else "No hay inventario registrado para ese centro y período.")


df = tech.resources_frame(conn, f["periodo"], rules, f["regiones"] or None)
if f["centros"] and not df.empty:
    df = df[df["centro_codigo"].isin(f["centros"])]
if df.empty:
    common.empty("No hay inventario tecnológico para este período y filtros.",
                 "Regístrelo a continuación o cárguelo como archivo en Datos y ETL.")
    st.markdown("#### Registrar inventario")
    inventory_form(f["periodo"])
    st.stop()

t = rules["tecnologia"]
df = df.copy()
df["centro"] = df["centro_nombre"].str.replace("Centro Educativo ", "", regex=False)
common.kpi_band([
    {"label": "Centros evaluados", "value": len(df)},
    {"label": "Conectividad escolar", "value": f"{df['tiene_internet'].mean() * 100:.1f}", "unit": "%",
     "help": "Centros con internet / centros evaluados × 100"},
    {"label": "Dispositivos por estudiante", "value": f"{df['dispositivos'].sum() / max(df['matriculados'].sum(), 1):.2f}",
     "help": "Dispositivos funcionales / estudiantes matriculados"},
    {"label": "Necesidad alta", "value": int((df["necesidad"] == "alta").sum()), "unit": "centros"},
    {"label": "Necesidad media", "value": int((df["necesidad"] == "media").sum()), "unit": "centros"},
])

t1, t2, t3, t4 = st.tabs(["Mapa de necesidades", "Centros prioritarios", "Comparar dos centros",
                          "Registrar inventario"])
with t1:
    fig = px.scatter(df, x="dispositivos_por_estudiante", y="velocidad_mbps", size="matriculados",
                     color="necesidad", color_discrete_map=common.NECESIDAD_COLORS, hover_name="centro",
                     hover_data={"region_nombre": True, "zona": True, "motivos": True, "matriculados": True},
                     category_orders={"necesidad": ["alta", "media", "baja"]}, size_max=22,
                     labels={"dispositivos_por_estudiante": "Dispositivos por estudiante",
                             "velocidad_mbps": "Velocidad de internet (Mbps)", "necesidad": "Necesidad",
                             "region_nombre": "Región", "zona": "Zona", "motivos": "Motivos",
                             "matriculados": "Matrícula"})
    fig.update_traces(marker=dict(line=dict(color="white", width=1), opacity=.85))
    for x, color, txt in ((t["dispositivos_por_estudiante_critico"], common.RED, "crítico"),
                          (t["dispositivos_por_estudiante_minimo"], common.AMBER, "mínimo")):
        fig.add_vline(x=x, line_dash="dot", line_color=color, line_width=1, annotation_text=f"{txt} {x}",
                      annotation_position="top right", annotation_font=dict(size=11, color=color))
    fig.add_hline(y=t["velocidad_minima_mbps"], line_dash="dot", line_color=common.AMBER, line_width=1,
                  annotation_text=f"mínimo {t['velocidad_minima_mbps']} Mbps", annotation_position="top right",
                  annotation_font=dict(size=11, color=common.AMBER))
    common.chart(fig, 430)
    common.note(f"Criterios configurables en Administración: sin internet o menos de "
                f"{t['dispositivos_por_estudiante_critico']} dispositivos por estudiante → <b>alta</b>; internet bajo "
                f"{t['velocidad_minima_mbps']} Mbps o menos de {t['dispositivos_por_estudiante_minimo']} → <b>media</b>. "
                "Los centros sin internet aparecen sobre el eje en 0 Mbps.")
    view = df.assign(tiene_internet=df["tiene_internet"].map({1: "Sí", 0: "No"}))
    common.table(view, ["centro_codigo", "centro", "zona", "matriculados", "tiene_internet", "velocidad_mbps",
                        "dispositivos_por_estudiante", "necesidad", "motivos"], rename={"centro": "Centro educativo"},
                 column_config={"Disp./estudiante": st.column_config.NumberColumn(format="%.2f")})
    common.csv_button(common.pretty(view), f"recursos_tecnologicos_{f['periodo']}.csv")
with t2:
    pr = tech.priority_list(df)
    common.note("Ordenados por nivel de necesidad, falta de internet, menor disponibilidad de dispositivos y mayor "
                "matrícula. La lista orienta una evaluación; la asignación la decide la dirección en Decisiones.")
    if pr.empty:
        common.empty("Ningún centro cumple los criterios de atención prioritaria.")
    else:
        common.table(pr, ["prioridad", "centro_codigo", "centro", "region_nombre", "necesidad", "motivos",
                          "matriculados", "dispositivos_por_estudiante"], rename={"centro": "Centro educativo"},
                     max_height=560)
        common.csv_button(common.pretty(pr), f"centros_prioritarios_tecnologia_{f['periodo']}.csv")
with t3:
    opts = dict(zip(df["centro_codigo"], df["centro_codigo"] + " " + df["centro"]))
    keys = list(opts)
    a, b = st.columns(2, gap="large")
    c1 = a.selectbox("Centro A", keys, index=keys.index("CE-021") if "CE-021" in keys else 0, format_func=opts.get)
    c2 = b.selectbox("Centro B", keys, index=keys.index("CE-005") if "CE-005" in keys else min(1, len(keys) - 1),
                     format_func=opts.get)
    for col, code in ((a, c1), (b, c2)):
        r = df[df["centro_codigo"] == code].iloc[0]
        with col:
            common.title_with_chips(r["centro"], [common.chip(f"necesidad {r['necesidad']}",
                                                              common.NECESIDAD_COLORS[r["necesidad"]])])
            common.note(f"{common.esc(r['region_nombre'])} · zona {r['zona']} · {int(r['matriculados'])} estudiantes")
            common.facts([
                {"k": "Internet", "v": f"{r['velocidad_mbps']:.0f} Mbps" if r["tiene_internet"] else "Sin acceso"},
                {"k": "Disp./estudiante", "v": f"{r['dispositivos_por_estudiante']:.2f}"},
                {"k": "Computadoras", "v": int(r["computadoras_funcionales"])},
                {"k": "Tabletas", "v": int(r["tabletas_funcionales"])},
            ])
            common.note(r["motivos"])
    hist = tech.resources_frame(conn, None, rules)
    hist = hist[hist["centro_codigo"].isin([c1, c2])].copy()
    if not hist.empty:
        hist["centro"] = hist["centro_nombre"].str.replace("Centro Educativo ", "", regex=False)
        fig = px.line(hist, x="periodo_codigo", y="dispositivos_por_estudiante", color="centro", markers=True,
                      labels={"periodo_codigo": "", "dispositivos_por_estudiante": "Dispositivos por estudiante",
                              "centro": ""})
        fig.update_traces(line_width=3, marker_size=9)
        st.markdown("#### Evolución de dispositivos por estudiante")
        common.chart(fig, 280)
with t4:
    inventory_form()
