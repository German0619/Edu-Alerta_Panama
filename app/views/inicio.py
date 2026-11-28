"""Pantalla 1 · Inicio: resumen ejecutivo con KPI (F57, F59, F61, F63, F64)."""
import pandas as pd
import plotly.express as px
import streamlit as st

import common
from edualerta.db import sql
from edualerta.services import followup, indicators, kpi, quality, recommendations, reports

common.guard("inicio")
conn, db = common.conn(), common.db()
rules = sql.get_rules(conn)

common.header("Resumen ejecutivo",
              "Qué estudiantes requieren atención, cómo responde la institución y en qué contexto escolar.")
f = common.filters_bar()
if not f["periodo"]:
    common.empty("Todavía no hay datos procesados.",
                 "Un perfil de Tecnología debe ejecutar el pipeline en <b>Datos y ETL</b>.")
    st.stop()
if db is None:
    st.warning("MongoDB no responde: los indicadores de alertas e intervenciones aparecen como «sin dato».",
               icon=":material/cloud_off:")

k = kpi.compute(conn, db, f["periodo"], rules, f["regiones"], f["centros"], f["grados"])
periods = sql.periods(conn)
pos = periods.index(f["periodo"])
prev_period = periods[pos - 1] if pos > 0 else None
kp = kpi.compute(conn, db, prev_period, rules, f["regiones"], f["centros"], f["grados"]) if prev_period else None

# ----------------------------------------------------------------- semáforo (elemento principal)
ind = indicators.indicator_frame(conn, f["periodo"], f["regiones"], f["centros"], f["grados"])
counts = ind["nivel_alerta"].value_counts().to_dict()
common.semaforo(counts, f"Estudiantes por nivel de riesgo · {f['periodo']}",
                f"{len(ind)} estudiantes evaluados con reglas explicables")


def item(key, higher_is_better=True):
    it = k[key]
    v = it["valor"]
    unit = "%" if it["unidad"] == "%" else ""
    if v is None:  # denominador cero (p. ej., sin casos) = «No aplica»; fuente caída = «sin dato»
        value, unit = ("No aplica" if it["denominador"] == 0 else "sin dato"), ""
    else:
        value = f"{v:.1f}" if it["unidad"] == "%" else (f"{v:.2f}" if isinstance(v, float) else f"{v}")
    delta, good = None, None
    if kp and v is not None and kp[key]["valor"] is not None:
        d = v - kp[key]["valor"]
        if abs(d) < 0.05:
            delta = f"sin cambio vs. {prev_period}"
        else:
            delta = f"{d:+.1f}{' pts' if it['unidad'] == '%' else ''} vs. {prev_period}"
            good = (d > 0) == higher_is_better
    if v is None and it["denominador"] == 0:
        delta = "sin casos todavía"
    if it["numerador"] is None:
        calc = "sin dato (fuente no disponible)"
    elif it["unidad"] in ("%", "disp./est."):  # razones: se muestra la división real
        calc = f"{it['numerador']} / {it['denominador']}"
    else:  # conteos: el total es contexto, no un divisor
        calc = f"{it['numerador']} (de {it['denominador']} alertas vigentes)"
    return {"label": it["nombre"], "value": value, "unit": unit, "delta": delta, "good": good,
            "help": f"{it['formula']} = {calc}. Fuente: {it['fuente']}."}


left, right = st.columns([3, 2], gap="large")
with left:
    common.kpi_band([item("tasa_asistencia"), item("tasa_aprobacion"),
                     item("alertas_prioritarias", higher_is_better=False)], "Rendimiento académico")
with right:
    common.kpi_band([item("alertas_sin_seguimiento", higher_is_better=False), item("intervenciones_realizadas")],
                    "Respuesta institucional")
q = quality.by_source(conn)
apto = bool(q["apto_para_decidir"].all()) if not q.empty else False
left, right = st.columns([3, 2], gap="large")
with left:
    common.kpi_band([
        item("conectividad_escolar"),
        {**item("disponibilidad_dispositivos"), "label": "Dispositivos por estudiante"},
        {"label": "Calidad de los datos", "value": "Apta" if apto else "Revisar",
         "delta": "completitud y consistencia ≥ 95 %" if apto else "alguna fuente bajo 95 %", "good": apto,
         "help": "Ver Administración › Gobierno de datos."},
    ], "Contexto escolar y datos")
with right:
    st.markdown('<div class="edu-group">Cómo leer estos indicadores</div>', unsafe_allow_html=True)
    common.note("Cada cifra se calcula desde la base de datos en cada ejecución del pipeline. Pase el cursor "
                "sobre <b>?</b> (o tóquelo) para ver la fórmula y el cálculo exacto. La variación compara con el período "
                "anterior: verde mejora, rojo empeora.")

# ----------------------------------------------------------------- alertas por centro + casos
left, right = st.columns([1.55, 1], gap="large")
dist = kpi.alert_distribution(conn, f["periodo"], f["regiones"], f["centros"], f["grados"])
dist = dist[dist["nivel_alerta"] != "regular"] if not dist.empty else dist
with left:
    st.markdown("### Centros con más alertas")
    if dist.empty:
        common.empty("Sin alertas para estos filtros.")
    else:
        top = dist.groupby("centro_codigo")["estudiantes"].sum().nlargest(10).index
        d = dist[dist["centro_codigo"].isin(top)].copy()
        d["centro"] = d["centro_nombre"].str.replace("Centro Educativo ", "", regex=False)
        order = d.groupby("centro")["estudiantes"].sum().sort_values().index.tolist()
        fig = px.bar(d, y="centro", x="estudiantes", color="nivel_alerta", orientation="h",
                     color_discrete_map=common.NIVEL_COLORS, hover_data={"centro_codigo": True},
                     category_orders={"centro": order, "nivel_alerta": ["prioritario", "preventivo"]},
                     labels={"centro": "", "estudiantes": "Estudiantes con alerta", "nivel_alerta": "Nivel"})
        common.chart(fig, 380)
with right:
    st.markdown("### Casos de seguimiento")
    if db is not None:
        cases = followup.cases_frame(db, centros=f["centros"] or None, periodo=f["periodo"],
                                     regiones=f["regiones"] or None, grados=f["grados"] or None)
        cnt = cases["estado"].value_counts() if not cases.empty else pd.Series(dtype=int)
        common.bars([(e, int(cnt.get(e, 0)), common.CASO_COLORS[e]) for e in followup.ESTADOS_CASO])
        if cases.empty:
            common.note("Aún no hay casos. Se abren en <b>Seguimiento</b> al confirmar una alerta.")
        else:
            prox = cases.dropna(subset=["proxima_revision"]).sort_values("proxima_revision").head(4)
            if not prox.empty:
                st.markdown("#### Próximas revisiones")
                common.table(prox, ["estudiante_codigo", "responsable", "proxima_revision", "estado"],
                             rename={"estado": "Estado del caso"})

# ----------------------------------------------------------------- recomendaciones
st.markdown("### Recomendaciones que esperan decisión")
if db is not None:
    recs = recommendations.decisions_frame(db, estados=["pendiente"], solo_vigentes=True)
    recs = recs[recs["vigente"]] if not recs.empty else recs
    if recs.empty:
        common.empty("No hay recomendaciones pendientes.")
    else:
        rows = "".join(
            f'<div class="edu-rec"><div class="score">{r["puntaje"]:.0f}</div><div>'
            f'<div class="tt">{common.esc(r["titulo"])}</div><div class="cr">{common.esc(r["criterio"])}</div></div>'
            f'<div>{common.chip("urgencia " + r["urgencia"], common.RED if r["urgencia"] == "alta" else common.AMBER)}'
            f'</div></div>' for r in recs.head(5).to_dict("records"))
        st.markdown(f'<div class="edu-recs">{rows}</div>', unsafe_allow_html=True)
        common.note(f"Se muestran 5 de {len(recs)} recomendaciones pendientes. La prioridad combina urgencia "
                    "(60 %) y estudiantes afectados (40 %). Se deciden en <b>Decisiones</b>.")

# ----------------------------------------------------------------- exportación
st.markdown("### Reporte ejecutivo")
kpi_rows = pd.DataFrame([{"KPI": v["nombre"],
                          # los conteos se exportan como enteros (no 6.0) aunque la columna mezcle tipos
                          "Valor": int(v["valor"]) if v["valor"] is not None and v["unidad"] in ("estudiantes", "alertas")
                          else v["valor"], "Unidad": v["unidad"], "Fórmula": v["formula"],
                          "Numerador": v["numerador"], "Denominador": v["denominador"], "Fuente": v["fuente"]}
                         for v in k.values()])
tablas = {}
if not dist.empty:
    tablas["Alertas por centro (top 15)"] = (dist.pivot_table(index=["centro_codigo", "centro_nombre"],
                                                               columns="nivel_alerta", values="estudiantes",
                                                               aggfunc="sum", fill_value=0)
                                             .reset_index().head(15)
                                             .rename(columns={"centro_codigo": "Código", "centro_nombre": "Centro",
                                                              "prioritario": "Prioritario",
                                                              "preventivo": "Preventivo"}))
if db is not None:
    r = recommendations.decisions_frame(db, solo_vigentes=True)
    if not r.empty and (f["regiones"] or f["centros"]):  # mismo alcance que los filtros del reporte
        cen = sql.query_df(conn, "SELECT codigo, region_codigo FROM centros")
        if f["regiones"]:
            cen = cen[cen["region_codigo"].isin(f["regiones"])]
        if f["centros"]:
            cen = cen[cen["codigo"].isin(f["centros"])]
        scope_c, scope_r = set(cen["codigo"]), set(cen["region_codigo"])
        r = r[r["objetivo"].map(lambda o: o.get("tipo") == "global"
                                or (o.get("tipo") == "region" and o.get("codigo") in scope_r)
                                or (o.get("tipo") == "centro" and o.get("codigo") in scope_c))]
    if not r.empty:
        tablas["Recomendaciones y decisiones"] = r[["puntaje", "titulo", "estado"]].head(15).rename(
            columns={"puntaje": "Prioridad", "titulo": "Recomendación", "estado": "Estado"})
pdf = reports.executive_pdf(f"Resumen ejecutivo {f['periodo']}", common.filters_label(f), k, tablas)
c1, c2, _ = st.columns([1, 1, 2.2])
with c1:
    st.download_button("Descargar PDF", pdf, f"reporte_ejecutivo_{f['periodo']}.pdf", "application/pdf",
                       icon=":material/picture_as_pdf:", type="primary", use_container_width=True)
with c2:
    common.csv_button(kpi_rows, f"kpi_{f['periodo']}.csv", "Descargar KPI (CSV)")
common.note("El reporte aplica los filtros de la barra lateral.")
