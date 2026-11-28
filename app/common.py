"""Utilidades compartidas de la interfaz: sesión, permisos, filtros, sistema visual y componentes.

Sistema visual "pizarra y tiza":
  pizarra  #183A34  barra de navegación superior y titulares (pizarrón escolar)
  tiza     #EEF2F0  superficies secundarias
  cobalto  #1D5FA8  acciones (tinta de bolígrafo)
  semáforo #C62E2E / #D68A00 / #2F8A5B  reservado a niveles de riesgo y necesidad
Tipografía: Bricolage Grotesque (titulares y cifras) + Figtree (texto).
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import plotly.io as pio  # noqa: E402
import streamlit as st  # noqa: E402

from edualerta.db import mongo, sql  # noqa: E402
from edualerta.services import auth  # noqa: E402

# ----------------------------------------------------------------- tokens
INK = "#1C2421"
MUTED = "#5E6B66"
LINE = "#D9E0DC"
SLATE = "#183A34"
CHALK = "#EEF2F0"
COBALT = "#1D5FA8"
RED, AMBER, GREEN = "#C62E2E", "#D68A00", "#2F8A5B"
GREY = "#8A9691"

NIVEL_COLORS = {"prioritario": RED, "preventivo": AMBER, "regular": GREEN}
NECESIDAD_COLORS = {"alta": RED, "media": AMBER, "baja": GREEN}
CASO_COLORS = {"pendiente": GREY, "en seguimiento": COBALT, "atendido": GREEN, "cerrado": SLATE}
ESTADO_ALERTA_COLORS = {"abierta": GREY, "confirmada": COBALT, "descartada": "#B0B8B4"}
ACCENT = COBALT
SERIES = [COBALT, "#3E8E7E", "#8A5A9E", "#C07A2C", "#4F6D8A", "#9C4F5A"]

FONT_BODY = "'Figtree', system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_HEAD = "'Bricolage Grotesque', 'Figtree', system-ui, sans-serif"

FONT_FACE = (Path(__file__).parent / "static" / "fonts" / "fonts.css").read_text("utf-8")

CSS = f"""
<style>
/* fuentes locales: app/static/fonts (sin dependencia de internet) */
{FONT_FACE}

:root {{ --edu-ink:{INK}; --edu-muted:{MUTED}; --edu-line:{LINE}; --edu-slate:{SLATE}; --edu-chalk:{CHALK};
        --edu-cobalt:{COBALT}; --edu-red:{RED}; --edu-amber:{AMBER}; --edu-green:{GREEN}; }}

/* tipografía */
.stApp, .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre) {{ font-family: {FONT_BODY}; }}
.stApp [data-testid="stIconMaterial"], .stApp [data-testid="stAlertDynamicIcon"],
.stApp [data-testid="stAlertDynamicIcon"] *, .stApp [data-testid^="stExpanderIcon"] {{
    font-family: "Material Symbols Rounded" !important; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp [data-testid="stMetricValue"] div, .edu-num {{ font-family: {FONT_HEAD} !important; }}
.stApp h1 {{ font-size: 2.15rem; font-weight: 700; letter-spacing: -0.02em; color: var(--edu-slate);
            line-height: 1.15; padding: 0; }}
.stApp h2 {{ font-size: 1.45rem; font-weight: 650; letter-spacing: -0.01em; color: var(--edu-slate); }}
.stApp h3 {{ font-size: 1.15rem; font-weight: 650; color: var(--edu-slate); padding-top: .6rem; }}
.stApp h4, .stApp h5 {{ font-size: 1rem; font-weight: 650; color: var(--edu-ink); }}
.stApp p, .stApp li {{ line-height: 1.55; }}

/* lienzo */
[data-testid="stDecoration"] {{ display: none; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1320px; }}
[data-testid="stToolbar"] {{ right: 1rem; }}

/* filtros globales: franja tiza bajo el encabezado */
.st-key-edu_filters {{ background: var(--edu-chalk); border-radius: 10px; padding: .55rem 1rem .75rem;
    margin: -.5rem 0 1.4rem; }}
.st-key-edu_filters [data-testid="stWidgetLabel"] p {{ font-size: .8rem; color: var(--edu-muted); }}
.st-key-edu_filters [data-baseweb="select"] > div {{ background: #fff; border-color: var(--edu-line); }}

/* menú de usuario (popover de la barra superior) */
.edu-user {{ display: flex; gap: .7rem; align-items: center; padding: .1rem 0 .8rem; min-width: 230px; }}
.edu-user .av {{ width: 40px; height: 40px; border-radius: 50%; background: var(--edu-slate); display: grid;
    place-items: center; font-family: {FONT_HEAD} !important; font-weight: 700; color: #fff; flex: none; }}
.edu-user .nm {{ font-weight: 700; line-height: 1.2; color: var(--edu-ink); }}
.edu-user .rl {{ font-size: .82rem; color: var(--edu-muted); line-height: 1.3; }}

/* encabezado de página */
.edu-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1.5rem;
    border-bottom: 1px solid var(--edu-line); padding-bottom: 1rem; margin-bottom: 1.4rem; flex-wrap: wrap; }}
.edu-head > div:first-child {{ flex: 1 1 480px; min-width: 0; }}
.edu-head h1 {{ margin: 0 !important; }}
.edu-head .lead {{ color: var(--edu-muted); margin: .35rem 0 0; max-width: 70ch; font-size: 1rem; }}
.edu-fresh {{ font-size: .82rem; color: var(--edu-muted); border: 1px solid var(--edu-line); border-radius: 999px;
    padding: .3rem .8rem; white-space: nowrap; margin-top: .4rem; }}
.edu-fresh b {{ color: var(--edu-ink); }}
.edu-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: .45rem;
    vertical-align: middle; }}

/* franja de indicadores (libreta) */
.edu-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    border-top: 2px solid var(--edu-slate); border-bottom: 1px solid var(--edu-line); margin: .2rem 0 1.6rem; }}
.edu-kpi {{ padding: .85rem 1rem .9rem; border-left: 1px solid var(--edu-line); }}
.edu-kpi:first-child {{ border-left: none; padding-left: .1rem; }}
.edu-kpi .lbl {{ font-size: .85rem; color: var(--edu-muted); display: flex; gap: .3rem; align-items: center;
    min-height: 2.4em; line-height: 1.2; position: relative; }}
.edu-kpi .lbl .q {{ cursor: help; border: 1px solid var(--edu-line); border-radius: 50%; width: 16px; height: 16px;
    font-size: .7rem; display: inline-grid; place-items: center; color: var(--edu-muted); flex: none; }}
.edu-kpi .lbl .q:hover, .edu-kpi .lbl .q:focus-visible {{ border-color: var(--edu-cobalt); color: var(--edu-cobalt);
    outline: none; }}
.edu-kpi .lbl .q::after {{ content: attr(data-tip); position: absolute; bottom: calc(100% + 6px); left: 0; right: 0;
    min-width: 230px; z-index: 30; background: var(--edu-slate); color: #fff; font-size: .82rem; font-weight: 400;
    line-height: 1.45; text-align: left; white-space: normal; padding: .6rem .75rem; border-radius: 6px;
    box-shadow: 0 8px 20px rgba(24,58,52,.22); opacity: 0; visibility: hidden; pointer-events: none;
    transition: opacity .12s ease, visibility .12s; }}
.edu-kpi:last-child .lbl .q::after {{ left: auto; }}
.edu-kpi .lbl .q:hover::after, .edu-kpi .lbl .q:focus::after {{ opacity: 1; visibility: visible; }}
.edu-kpi .val {{ font-family: {FONT_HEAD} !important; font-size: 1.9rem; font-weight: 650; color: var(--edu-ink);
    line-height: 1.1; font-variant-numeric: tabular-nums; margin-top: .25rem; }}
.edu-kpi .val small {{ font-size: .95rem; font-weight: 500; color: var(--edu-muted); margin-left: .15rem; }}
.edu-kpi .dl {{ font-size: .82rem; margin-top: .3rem; color: var(--edu-muted); }}
.edu-kpi .dl.good {{ color: var(--edu-green); }} .edu-kpi .dl.bad {{ color: var(--edu-red); }}
.edu-kpiwrap {{ container-type: inline-size; }}
@container (max-width: 560px) {{
  .edu-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .edu-kpi, .edu-kpi:first-child {{ border-left: none; padding-left: .1rem; }}
  .edu-kpi:nth-child(even) {{ border-left: 1px solid var(--edu-line); padding-left: .9rem; }}
  .edu-kpi:nth-child(n+3) {{ border-top: 1px solid var(--edu-line); }}
  .edu-kpi:nth-child(odd) .lbl .q::after {{ left: 0; right: auto; }}
  .edu-kpi:nth-child(even) .lbl .q::after {{ left: auto; right: 0; }}
}}
@container (max-width: 300px) {{
  .edu-kpis {{ grid-template-columns: 1fr; }}
  .edu-kpi:nth-child(even) {{ border-left: none; padding-left: .1rem; }}
  .edu-kpi:nth-child(n+2) {{ border-top: 1px solid var(--edu-line); }}
}}
.edu-group {{ font-size: .9rem; font-weight: 700; color: var(--edu-slate); margin: .4rem 0 .1rem; }}

/* semáforo */
.edu-sem {{ margin: .3rem 0 1.8rem; }}
.edu-sem .bar {{ display: flex; height: 22px; border-radius: 4px; overflow: hidden; }}
.edu-sem .bar span {{ display: block; height: 100%; }}
.edu-sem .legend {{ display: flex; gap: 2.2rem; margin-top: .65rem; flex-wrap: wrap; }}
.edu-sem .legend div {{ display: flex; flex-direction: column; }}
.edu-sem .legend .n {{ font-family: {FONT_HEAD} !important; font-size: 1.6rem; font-weight: 700;
    font-variant-numeric: tabular-nums; line-height: 1.1; }}
.edu-sem .legend .t {{ font-size: .85rem; color: var(--edu-muted); }}
.edu-sem .title {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: .5rem;
    gap: 1rem; flex-wrap: wrap; }}
.edu-sem .title h3 {{ margin: 0; padding: 0; }}
.edu-sem .title span {{ color: var(--edu-muted); font-size: .9rem; }}

/* chips y listas */
.edu-chip {{ display: inline-block; white-space: nowrap; flex: none; padding: 1px 9px; border-radius: 4px; font-size: .78rem; font-weight: 700;
    color: #fff !important; vertical-align: middle; line-height: 1.6; }}
.edu-chip.soft {{ background: var(--edu-chalk); color: var(--edu-ink) !important; font-weight: 400; }}
.edu-reasons {{ list-style: none; padding: 0; margin: .3rem 0 .8rem; }}
.edu-reasons li.bad::before {{ content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--edu-red);
    flex: none; transform: translateY(-1px); }}
.edu-reasons li {{ display: flex; gap: .6rem; align-items: baseline; padding: .35rem 0;
    border-bottom: 1px dashed var(--edu-line); }}
.edu-bars {{ display: flex; flex-direction: column; gap: .55rem; margin: .4rem 0 .2rem; }}
.edu-bars .row {{ display: grid; grid-template-columns: minmax(5.5rem, 9.5rem) minmax(48px, 1fr) 2rem; gap: .7rem; align-items: center;
    font-size: .92rem; }}
.edu-bars .track {{ background: var(--edu-chalk); height: 10px; border-radius: 3px; overflow: hidden; }}
.edu-bars .fill {{ height: 100%; }}
.edu-bars .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }}
.edu-recs {{ border-top: 1px solid var(--edu-line); }}
.edu-rec {{ display: grid; grid-template-columns: 3.2rem 1fr auto; gap: 1rem; padding: .75rem 0;
    border-bottom: 1px solid var(--edu-line); align-items: start; }}
.edu-rec .score {{ font-family: {FONT_HEAD} !important; font-size: 1.45rem; font-weight: 700; color: var(--edu-slate);
    font-variant-numeric: tabular-nums; line-height: 1.1; }}
.edu-rec .tt {{ font-weight: 700; }}
.edu-rec .cr {{ font-size: .86rem; color: var(--edu-muted); margin-top: .1rem; }}
.edu-panel {{ border: 1px solid var(--edu-line); border-radius: 8px; padding: 1rem 1.1rem; }}
.edu-empty {{ border: 1px dashed var(--edu-line); border-radius: 8px; padding: 1.1rem 1.2rem; color: var(--edu-muted); }}
.edu-empty b {{ color: var(--edu-ink); }}
.edu-note {{ font-size: .85rem; color: var(--edu-muted); }}
.edu-facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: .1rem 1.2rem;
    margin: .3rem 0 .8rem; }}
.edu-facts > div {{ padding: .45rem 0; border-bottom: 1px solid var(--edu-line); }}
.edu-facts .k {{ font-size: .8rem; color: var(--edu-muted); }}
.edu-facts .v {{ font-family: {FONT_HEAD} !important; font-size: 1.25rem; font-weight: 650;
    font-variant-numeric: tabular-nums; }}
.edu-facts .d {{ font-size: .78rem; }}
.edu-facts .d.bad {{ color: var(--edu-red); }} .edu-facts .d.good {{ color: var(--edu-green); }}

/* línea de tiempo y pasos */
.stApp ul.edu-tl {{ list-style: none !important; margin: .3rem 0 0 .45rem !important; padding: 0 !important;
    border-left: 2px solid var(--edu-line); }}
.stApp ul.edu-tl > li {{ position: relative; list-style: none; margin: 0 !important; padding: 0 0 .95rem 1.1rem !important; }}
.edu-tl .dot {{ position: absolute; left: -7px; top: .3rem; width: 12px; height: 12px; border-radius: 50%;
    border: 2px solid #fff; box-sizing: border-box; }}
.edu-tl .when {{ font-size: .8rem; color: var(--edu-muted); font-variant-numeric: tabular-nums; }}
.edu-tl .what {{ font-weight: 700; font-size: .93rem; }}
.edu-tl .txt {{ font-size: .92rem; }}
.edu-tl .who {{ font-size: .8rem; color: var(--edu-muted); }}
.edu-step {{ display: flex; gap: .7rem; align-items: baseline; margin: .2rem 0 .5rem; }}
.edu-step .n {{ font-family: {FONT_HEAD} !important; font-weight: 800; color: #fff; background: var(--edu-slate);
    width: 1.6rem; height: 1.6rem; border-radius: 50%; display: inline-grid; place-items: center; flex: none;
    font-size: .9rem; }}
.edu-step.done .n {{ background: var(--edu-green); }}
.edu-step.off .n {{ background: #B0B8B4; }}
.edu-step .t {{ font-weight: 700; color: var(--edu-slate); }}
.edu-step .s {{ font-size: .85rem; color: var(--edu-muted); }}
.edu-title {{ display: flex; gap: .6rem; align-items: center; flex-wrap: wrap; margin: .4rem 0 .2rem; }}
.edu-title h3 {{ margin: 0; padding: 0; }}

/* tabla de calor */
.edu-heat {{ overflow-x: auto; border-top: 2px solid var(--edu-slate); }}
.edu-heat table {{ width: 100%; border-collapse: collapse; font-size: .9rem; font-variant-numeric: tabular-nums; }}
.edu-heat th {{ text-align: right; font-weight: 700; color: var(--edu-muted); font-size: .8rem; padding: .55rem .6rem;
    border-bottom: 1px solid var(--edu-line); white-space: nowrap; }}
.edu-heat th:first-child, .edu-heat td:first-child {{ text-align: left; }}
.edu-heat td {{ font-family: {FONT_HEAD} !important; font-size: .88rem; text-align: right; padding: .42rem .6rem; border-bottom: 1px solid #EDF1EF; white-space: nowrap; }}
.edu-heat tr.refrow td {{ background: var(--edu-chalk); font-weight: 700; }}

/* matriz de alineación y procesos */
.edu-matrix td, .edu-matrix th {{ text-align: left !important; white-space: normal !important;
    font-family: {FONT_BODY} !important; font-size: .9rem; vertical-align: top; }}
.stApp ol.edu-flowlist {{ counter-reset: paso; list-style: none; padding: 0 !important; margin: .4rem 0 0 !important; }}
.stApp ol.edu-flowlist > li {{ counter-increment: paso; display: grid; grid-template-columns: 1.8rem 1fr; gap: .5rem;
    padding: .5rem 0 !important; margin: 0 !important; border-top: 1px solid var(--edu-line); }}
.edu-flowlist > li::before {{ content: counter(paso); font-family: {FONT_HEAD}; font-weight: 800; color: var(--edu-muted); }}
.edu-flowlist.tobe > li::before {{ color: var(--edu-cobalt); }}

/* widgets */
.stTabs [data-baseweb="tab-list"] {{ gap: 1.4rem; border-bottom: 1px solid var(--edu-line); }}
.stTabs [data-baseweb="tab"] {{ padding-left: 0; padding-right: 0; }}
.stTabs [data-baseweb="tab"] p {{ font-size: .97rem; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.2rem; }}
div[data-testid="stMetric"] {{ border-left: 1px solid var(--edu-line); padding: .2rem 0 .2rem .9rem; }}
div[data-testid="stMetricValue"] div {{ font-size: 1.6rem; font-weight: 650; }}
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ border-radius: 6px; font-weight: 700; }}
[data-testid="stExpander"] details {{ border-radius: 8px; border-color: var(--edu-line); }}
[data-testid="stForm"] {{ border-color: var(--edu-line); border-radius: 8px; }}
[data-testid="stDataFrame"] {{ border: 1px solid var(--edu-line); border-radius: 6px; }}
[data-testid="stAlert"] {{ border-radius: 8px; }}
.stApp a {{ color: var(--edu-cobalt); }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""

# ----------------------------------------------------------------- Plotly
pio.templates["edu"] = go.layout.Template(layout=dict(
    font=dict(family="Figtree, system-ui, sans-serif", size=13, color=INK),
    colorway=SERIES,
    paper_bgcolor="white", plot_bgcolor="white",
    xaxis=dict(gridcolor="#E7ECE9", linecolor=LINE, zeroline=False, ticks="", automargin=True,
               title=dict(font=dict(size=12, color=MUTED), standoff=10), tickfont=dict(color=MUTED)),
    yaxis=dict(gridcolor="#E7ECE9", linecolor=LINE, zeroline=False, ticks="", automargin=True,
               title=dict(font=dict(size=12, color=MUTED), standoff=10), tickfont=dict(color=MUTED)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                font=dict(size=12, color=INK)),
    margin=dict(l=4, r=12, t=40, b=4),
    hoverlabel=dict(font=dict(family="Figtree, sans-serif", size=13), bgcolor="white",
                    bordercolor=LINE),
    title=dict(font=dict(family="Bricolage Grotesque, sans-serif", size=15, color=SLATE), x=0, xanchor="left"),
    coloraxis=dict(colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=MUTED, size=11))),
    bargap=0.25,
))
pio.templates.default = "plotly_white+edu"


def chart(fig, height: int = 360, **kwargs):
    """Grafica con la plantilla del sistema (theme=None evita que Streamlit la sobrescriba)."""
    fig.update_layout(height=height, legend_title_text="", plot_bgcolor="white", paper_bgcolor="white")
    return st.plotly_chart(fig, use_container_width=True, theme=None,
                           config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                           **kwargs)


# ----------------------------------------------------------------- tablas con encabezados legibles
LABELS = {
    "_id": "ID", "estudiante_codigo": "Estudiante", "codigo": "Código", "centro_codigo": "Centro",
    "centro_nombre": "Centro educativo", "centro": "Centro educativo", "region_codigo": "Cód. región",
    "region_nombre": "Región", "region": "Región", "periodo_codigo": "Período", "grado": "Grado",
    "nivel": "Nivel", "nivel_alerta": "Nivel", "estado": "Estado", "caso_id": "Caso",
    "asistencia_pct": "Asistencia %", "promedio": "Promedio", "max_ausencias_consecutivas": "Aus. consecutivas",
    "ausencias_justificadas": "Aus. justificadas", "asignaturas_reprobadas": "Asig. reprobadas",
    "motivos": "Motivos", "responsable": "Responsable", "rol_responsable": "Rol",
    "n_intervenciones": "Intervenciones", "ultima_intervencion": "Última intervención",
    "proxima_revision": "Próxima revisión", "abierto_en": "Abierto", "zona": "Zona", "dependencia": "Dependencia",
    "matriculados": "Matrícula", "tiene_internet": "Internet", "velocidad_mbps": "Velocidad (Mbps)",
    "computadoras_funcionales": "Computadoras", "tabletas_funcionales": "Tabletas",
    "dispositivos_por_estudiante": "Disp./estudiante", "necesidad": "Necesidad", "prioridad": "Prioridad",
    "estudiantes": "Estudiantes", "centros": "Centros", "prioritarios": "Prioritarios",
    "preventivos": "Preventivos", "aprobacion_pct": "Aprobación %", "prioritarios_pct": "% prioritarios",
    "conectividad_pct": "Conectividad %", "alertas_regionales": "Criterios desfavorables",
    "n_criterios_desfavorables": "N.º criterios", "muestra_suficiente": "Muestra suficiente",
    "fecha": "Fecha", "tipo": "Tipo", "descripcion": "Descripción", "detalle": "Detalle", "autor": "Autor",
    "origen": "Origen", "usuario": "Usuario", "evento": "Evento", "registrado_por": "Registrado por",
    "estado_caso_resultante": "Estado resultante", "genero": "Género", "anio_nacimiento": "Año nac.",
    "estado_matricula": "Matrícula", "nombre": "Nombre", "nivel_educativo": "Nivel educativo",
    "titulo": "Recomendación", "criterio": "Criterio", "urgencia": "Urgencia", "alcance": "Alcance",
    "puntaje": "Prioridad", "cumplimiento": "Cumplimiento", "fecha_revision": "Revisión",
    "riesgo_max": "Riesgo máx.", "indicador": "Indicador", "valor": "Valor", "referencia": "Referencia",
    "fuente": "Fuente", "archivo": "Archivo", "fila": "Fila", "motivo": "Motivo", "datos": "Datos",
    "registros": "Registros", "accion": "Acción", "entidad": "Entidad", "entidad_id": "Registro",
    "perfil": "Perfil", "asignatura": "Asignatura", "nota": "Nota", "momento": "Momento",
    "leidos": "Leídos", "aceptados": "Aceptados", "rechazados": "Rechazados", "omitidos": "Omitidos",
    "inicio": "Inicio", "fin": "Fin", "disparador": "Disparador", "id": "N.º",
    "completitud_pct": "Completitud %", "consistencia_pct": "Consistencia %", "aceptacion_pct": "Aceptación %",
    "apto_para_decidir": "Apta para decidir", "incompletos": "Incompletos", "duplicados": "Duplicados",
    "inconsistentes": "Inconsistentes", "archivos": "Archivos", "cobertura_pct": "Cobertura %",
    "con_indicadores": "Con indicadores", "probabilidad": "Probabilidad", "impacto": "Impacto",
    "control": "Control", "riesgo_matriz": "Riesgo de la matriz",
}
INT_COLS = {"max_ausencias_consecutivas", "ausencias_justificadas", "asignaturas_reprobadas", "grado",
            "n_intervenciones", "episodios_ausencia", "matriculados", "estudiantes", "centros"}
_COLORED = {"Nivel": NIVEL_COLORS, "Necesidad": NECESIDAD_COLORS, "Estado del caso": CASO_COLORS}


def pretty(df: pd.DataFrame, cols: list[str] | None = None, rename: dict | None = None) -> pd.DataFrame:
    out = df[cols].copy() if cols else df.copy()
    for c in out.columns:
        if out[c].dtype.kind == "f" and out[c].dropna().apply(float.is_integer).all() and c in INT_COLS:
            out[c] = out[c].astype("Int64")
        if out[c].dtype == object or str(out[c].dtype).startswith("category"):
            out[c] = out[c].astype(object).where(out[c].notna(), "—")
            out[c] = out[c].map(lambda v: "—" if v is None or v == "None" else v)
        if out[c].dtype == bool:
            out[c] = out[c].map({True: "Sí", False: "No"})
    return out.rename(columns={**LABELS, **(rename or {})})


def table(df: pd.DataFrame, cols: list[str] | None = None, rename: dict | None = None, max_height: int = 420,
          color_cols: dict | None = None, **kwargs):
    """st.dataframe con encabezados en español, «—» para vacíos, altura ajustada y semáforo en texto."""
    view = pretty(df, cols, rename)
    height = min(max_height, 36 * (len(view) + 1) + 4)
    colors = {**_COLORED, **(color_cols or {})}
    targets = [c for c in view.columns if c in colors]
    data = view
    if targets:
        def paint(col):
            cmap = colors[col.name]
            return [f"color: {cmap[v]}; font-weight: 700" if v in cmap else "" for v in col]
        data = view.style.apply(paint, subset=targets).format(precision=1, na_rep="—")
    return st.dataframe(data, hide_index=True, use_container_width=True, height=height, **kwargs)


# ----------------------------------------------------------------- componentes HTML
def esc(x) -> str:
    return html.escape(str(x))


TERMS = {"caso_abierto": "caso abierto", "intervencion": "intervención", "observacion": "observación",
         "diagnostico": "diagnóstico", "nivel_actualizado": "nivel actualizado", "sin_criterios": "sin criterios vigentes",
         "cambio_estado": "cambio de estado", "vigente_nuevamente": "vigente de nuevo",
         "recomendacion_generada": "recomendación generada", "decision_aprobar": "decisión: aprobar",
         "decision_posponer": "decisión: posponer", "decision_rechazar": "decisión: rechazar",
         "decision_solicitar_revision": "decisión: solicitar revisión", "cumplimiento": "cumplimiento"}


def term(text) -> str:
    """Convierte claves internas en texto legible ("caso_abierto" → "caso abierto")."""
    t = str(text)
    for k in sorted(TERMS, key=len, reverse=True):
        t = t.replace(k, TERMS[k])
    return t.replace("_", " ")


def chip(text: str, color: str) -> str:
    return f'<span class="edu-chip" style="background:{color}">{esc(text)}</span>'


def soft_chip(text: str) -> str:
    return f'<span class="edu-chip soft">{esc(text)}</span>'


def nivel_chip(nivel: str) -> str:
    return chip(nivel, NIVEL_COLORS.get(nivel, GREY))


def header(title: str, lead: str | None = None, fresh: bool = True):
    pill = ""
    if fresh:
        row = conn().execute("SELECT id, fin, estado FROM ejecuciones_etl WHERE estado != 'en_curso' "
                             "ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            color = {"exitosa": GREEN, "con_advertencias": AMBER, "fallida": RED}.get(row["estado"], GREY)
            when = pd.to_datetime(row["fin"]).strftime("%d/%m/%Y %H:%M")
            pill = (f'<div class="edu-fresh" title="Estado de la ejecución: {esc(row["estado"])}">'
                    f'<span class="edu-dot" style="background:{color}"></span>Datos al <b>{when}</b>'
                    f' (ETL n.º {row["id"]})</div>')
        else:
            pill = '<div class="edu-fresh"><span class="edu-dot" style="background:#C62E2E"></span>Sin datos procesados</div>'
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    st.markdown(f'<div class="edu-head"><div><h1>{esc(title)}</h1>{lead_html}</div>{pill}</div>',
                unsafe_allow_html=True)
    st.caption(
        "Datos sintéticos de demostración: estudiantes, centros, regiones e indicadores del escenario no describen "
        "la realidad de Panamá. Las estadísticas de MEDUCA se usan solo como referencia en el documento y no "
        "se procesan en este sistema."
    )


def kpi_band(items: list[dict], group: str | None = None):
    """Franja de indicadores. item: label, value, unit, delta (str), good (bool|None), help."""
    cells = []
    for it in items:
        # Tooltip propio (no `title`): aparece al instante con el cursor, con Tab o al tocarlo en pantallas táctiles.
        help_ = (f'<span class="q" tabindex="0" role="img" aria-label="Cómo se calcula: {esc(it["help"])}" '
                 f'data-tip="{esc(it["help"])}">?</span>') if it.get("help") else ""
        unit = f'<small>{esc(it["unit"])}</small>' if it.get("unit") else ""
        dl = ""
        if it.get("delta"):
            cls = "good" if it.get("good") is True else "bad" if it.get("good") is False else ""
            dl = f'<div class="dl {cls}">{esc(it["delta"])}</div>'
        cells.append(f'<div class="edu-kpi"><div class="lbl">{esc(it["label"])}{help_}</div>'
                     f'<div class="val">{esc(it["value"])}{unit}</div>{dl}</div>')
    g = f'<div class="edu-group">{esc(group)}</div>' if group else ""
    st.markdown(f'<div class="edu-kpiwrap">{g}<div class="edu-kpis">{"".join(cells)}</div></div>',
                unsafe_allow_html=True)


def facts(items: list[dict]):
    """Rejilla compacta de datos: k, v, d (delta opcional), good."""
    cells = []
    for it in items:
        d = ""
        if it.get("d"):
            cls = "good" if it.get("good") is True else "bad" if it.get("good") is False else ""
            d = f'<div class="d {cls}">{esc(it["d"])}</div>'
        cells.append(f'<div><div class="k">{esc(it["k"])}</div><div class="v">{esc(it["v"])}</div>{d}</div>')
    st.markdown(f'<div class="edu-facts">{"".join(cells)}</div>', unsafe_allow_html=True)


def semaforo(counts: dict, title: str, note: str = ""):
    total = sum(counts.values()) or 1
    seg = "".join(f'<span style="width:{counts.get(k, 0) / total * 100:.2f}%;background:{NIVEL_COLORS[k]}" '
                  f'title="{k}: {counts.get(k, 0)}"></span>' for k in ("prioritario", "preventivo", "regular"))
    names = {"prioritario": "prioritario: revisar primero", "preventivo": "preventivo: vigilar",
             "regular": "regular: sin señales"}
    leg = "".join(f'<div><span class="n" style="color:{NIVEL_COLORS[k]}">{counts.get(k, 0)}</span>'
                  f'<span class="t">{counts.get(k, 0) / total * 100:.1f} % · {names[k]}</span></div>'
                  for k in ("prioritario", "preventivo", "regular"))
    st.markdown(f'<div class="edu-sem"><div class="title"><h3>{esc(title)}</h3><span>{esc(note)}</span></div>'
                f'<div class="bar" role="img" aria-label="Distribución de niveles de riesgo">{seg}</div>'
                f'<div class="legend">{leg}</div></div>', unsafe_allow_html=True)


def bars(rows: list[tuple[str, int, str]]):
    """Barras horizontales simples: (etiqueta, valor, color)."""
    mx = max((v for _, v, _ in rows), default=1) or 1
    html_rows = "".join(
        f'<div class="row"><span>{esc(lbl)}</span><div class="track"><div class="fill" '
        f'style="width:{v / mx * 100:.1f}%;background:{c}"></div></div><span class="num">{v}</span></div>'
        for lbl, v, c in rows)
    st.markdown(f'<div class="edu-bars">{html_rows}</div>', unsafe_allow_html=True)


def timeline(rows: list[dict]):
    """rows: when, what, txt, who, color."""
    items = "".join(
        f'<li><span class="dot" style="background:{r.get("color", COBALT)}"></span>'
        f'<div class="when">{esc(r.get("when", ""))}</div>'
        f'<div class="what">{esc(term(r.get("what", "")))}</div>'
        + (f'<div class="txt">{esc(r["txt"])}</div>' if r.get("txt") else "")
        + (f'<div class="who">{esc(r["who"])}</div>' if r.get("who") else "") + "</li>" for r in rows)
    st.markdown(f'<ul class="edu-tl">{items}</ul>', unsafe_allow_html=True)


def step(n: int, title: str, sub: str = "", state: str = ""):
    """Paso numerado de un proceso real (revisión → caso → intervención). state: done | off | ''."""
    s = f'<div class="s">{sub}</div>' if sub else ""
    st.markdown(f'<div class="edu-step {state}"><span class="n">{"✓" if state == "done" else n}</span>'
                f'<div><div class="t">{esc(title)}</div>{s}</div></div>', unsafe_allow_html=True)


def title_with_chips(title: str, chips: list[str]):
    st.markdown(f'<div class="edu-title"><h3>{esc(title)}</h3>{"".join(chips)}</div>', unsafe_allow_html=True)


def fmt_date(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return "—"
    try:
        return pd.to_datetime(v).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(v)


def heat_table(df: pd.DataFrame, cols: dict, ref: dict, key_col: str, key_label: str, higher_better: dict,
               fmt: dict | None = None):
    """Tabla HTML con celdas coloreadas según la distancia a una referencia (verde mejor, rojo peor)."""
    fmt = fmt or {}
    head = f"<th>{esc(key_label)}</th>" + "".join(f"<th>{esc(v)}</th>" for v in cols.values())
    ref_row = f"<td><i>Referencia nacional</i></td>" + "".join(
        f"<td class='ref'>{fmt.get(c, '{:.1f}').format(ref[c]) if ref.get(c) is not None else '—'}</td>"
        for c in cols)
    body = []
    for r in df.to_dict("records"):
        tds = [f"<td><b>{esc(r[key_col])}</b></td>"]
        for c in cols:
            v, base = r.get(c), ref.get(c)
            if v is None or pd.isna(v):
                tds.append("<td>—</td>")
                continue
            style = ""
            if base:
                rel = (v - base) / abs(base) * (1 if higher_better.get(c, True) else -1)
                a = min(abs(rel) * 2.2, 0.55)
                color = "47,138,91" if rel > 0 else "198,46,46"
                if abs(rel) > 0.01:
                    style = f" style='background: rgba({color},{a:.2f})'"
            tds.append(f"<td{style}>{fmt.get(c, '{:.1f}').format(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    st.markdown(f"<div class='edu-heat'><table><thead><tr>{head}</tr></thead><tbody><tr class='refrow'>{ref_row}</tr>"
                f"{''.join(body)}</tbody></table></div>", unsafe_allow_html=True)


def empty(title: str, body: str = ""):
    st.markdown(f'<div class="edu-empty"><b>{esc(title)}</b><br>{body}</div>', unsafe_allow_html=True)


def note(text: str):
    st.markdown(f'<p class="edu-note">{text}</p>', unsafe_allow_html=True)


# ----------------------------------------------------------------- sesión y permisos
def conn():
    """Conexión SQLite por sesión de usuario."""
    if "_sql" not in st.session_state:
        c = sql.connect()
        sql.init_schema(c)
        st.session_state["_sql"] = c
    return st.session_state["_sql"]


def db():
    """Base MongoDB o None si no responde (la app se degrada sin caerse, F82)."""
    return mongo.get_db() if mongo.ping() else None


def require_db():
    d = db()
    if d is None:
        st.error("MongoDB no responde, así que alertas, seguimiento y decisiones no están disponibles. "
                 "Revise el contenedor `mongo` o la variable MONGO_URI.", icon=":material/cloud_off:")
        st.stop()
    return d


def user() -> dict | None:
    return st.session_state.get("user")


def can(accion: str) -> bool:
    return auth.can(user(), accion)


def guard(pagina: str) -> dict:
    u = user()
    if not auth.can_view(u, pagina):
        st.error("Su perfil no tiene acceso a esta pantalla (F73).", icon=":material/lock:")
        st.stop()
    return u


# ----------------------------------------------------------------- filtros globales (F05, F60)
def filters_bar(show_grade: bool = True) -> dict:
    """Franja de filtros bajo el encabezado de la pantalla; los valores se conservan entre pantallas."""
    c = conn()
    periods = sql.periods(c)
    if not periods:
        st.info("Aún no hay indicadores. Ejecute el pipeline en Datos y ETL.", icon=":material/info:")
        return {"periodo": None, "regiones": [], "centros": [], "grados": []}
    reg = sql.query_df(c, "SELECT codigo, nombre FROM regiones ORDER BY nombre")
    cen = sql.query_df(c, "SELECT codigo, nombre, region_codigo FROM centros ORDER BY codigo")
    if st.session_state.get("f_periodo") not in periods:
        st.session_state["f_periodo"] = periods[-1]
    reg_map = dict(zip(reg["codigo"], reg["nombre"]))
    st.session_state["f_regiones"] = [x for x in st.session_state.get("f_regiones", []) if x in reg_map]
    with st.container(key="edu_filters"):
        cols = st.columns([1, 1.7, 2.5, 1.2] if show_grade else [1, 1.9, 2.9], vertical_alignment="bottom")
        periodo = cols[0].selectbox("Período", periods[::-1], key="f_periodo")
        regiones = cols[1].multiselect("Región", list(reg_map), format_func=lambda x: reg_map[x],
                                       key="f_regiones", placeholder="Todas")
        cen_opts = cen[cen["region_codigo"].isin(regiones)] if regiones else cen
        cen_map = dict(zip(cen_opts["codigo"], cen_opts["codigo"] + " " + cen_opts["nombre"].str.replace(
            "Centro Educativo ", "", regex=False)))
        st.session_state["f_centros"] = [x for x in st.session_state.get("f_centros", []) if x in cen_map]
        centros = cols[2].multiselect("Centro educativo", list(cen_map), format_func=lambda x: cen_map[x],
                                      placeholder="Todos", key="f_centros")
        grados = cols[3].multiselect("Grado", list(range(7, 13)), key="f_grados", placeholder="Todos",
                                     format_func=lambda g: f"{g}.º") if show_grade else []
    return {"periodo": periodo, "regiones": regiones, "centros": centros, "grados": grados}


FILTER_KEYS = ("f_periodo", "f_regiones", "f_centros", "f_grados")


def persist_filters() -> None:
    """Conserva los filtros al navegar entre pantallas que no los muestran."""
    for k in FILTER_KEYS:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def filters_label(f: dict) -> dict:
    return {"Período": f.get("periodo") or "-", "Regiones": ", ".join(f.get("regiones") or []) or "Todas",
            "Centros": ", ".join(f.get("centros") or []) or "Todos",
            "Grados": ", ".join(map(str, f.get("grados") or [])) or "Todos"}


def csv_button(df: pd.DataFrame, filename: str, label: str = "Descargar CSV", key: str | None = None):
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"), file_name=filename, mime="text/csv",
                       key=key or f"dl_{filename}", icon=":material/download:")


def last_run_banner():
    """Compatibilidad: el estado de los datos ahora se muestra en el encabezado (header)."""
    return None


def student_code(text: str | None) -> str:
    """Normaliza un código escrito a mano igual que el ETL ('e42', 'E_42', ' e-0042 ' → 'E-0042').

    Si el texto no es un código completo (p. ej. '004'), lo devuelve en mayúsculas para búsquedas parciales.
    """
    from edualerta.etl import transform
    t = (text or "").strip()
    return transform.norm_student(pd.Series([t])).iloc[0] or t.upper()
