"""Pantalla 8 · Administración: reglas, perfiles, auditoría, gobierno de datos y automatización (F72-F86)."""
import os
import subprocess
import sys

import pandas as pd
import streamlit as st

import common
from common import esc
from edualerta import config
from edualerta.db import mongo, sql
from edualerta.etl import pipeline
from edualerta.services import audit, auth, quality
from edualerta.services.recommendations import risk_level

u = common.guard("administracion")
conn = common.conn()

common.header("Administración",
              "Reglas del sistema, perfiles de acceso, auditoría, gobierno de datos y automatización.")
t_ali, t_reg, t_perf, t_aud, t_gob, t_auto, t_sys = st.tabs(
    ["Alineación del SIG", "Reglas", "Perfiles y acceso", "Auditoría", "Gobierno de datos",
     "Automatización y pruebas", "Estado del sistema"])

MATRIZ = [
    ("Recopilar datos", "F07–F13", "Python, CSV, JSON, GeoJSON", "Determinar fuentes disponibles", "Datos y ETL"),
    ("Validar y transformar", "F14–F22", "Pipeline ETL", "Aceptar o corregir información", "Datos y ETL"),
    ("Consolidar registros", "F23–F28", "SQLite y MongoDB", "Disponer de información integrada", "Seguimiento › Perfil"),
    ("Monitorear indicadores", "F29–F35", "Python y SQL", "Detectar señales de riesgo", "Inicio · Seguimiento"),
    ("Revisar alertas", "F36–F38", "Streamlit y MongoDB", "Confirmar casos y asignar responsables", "Seguimiento"),
    ("Ejecutar seguimiento", "F39–F44", "MongoDB", "Registrar y evaluar intervenciones", "Seguimiento › Casos"),
    ("Analizar contexto escolar", "F45–F56", "SQL, Python y GeoJSON", "Identificar carencias y brechas",
     "Tecnología escolar · Regiones"),
    ("Analizar resultados", "F57–F64", "Dashboard", "Interpretar tendencias y KPI", "Inicio · Análisis"),
    ("Decidir y priorizar", "F65–F71", "Reglas y registro gerencial", "Aprobar acciones y evaluar riesgos",
     "Decisiones"),
    ("Controlar y mejorar", "F72–F86", "Auditoría y automatización", "Verificar calidad y continuidad",
     "Administración"),
]
AS_IS = ["Los docentes registran asistencia y calificaciones.", "Los datos quedan dispersos en archivos o sistemas.",
         "El personal revisa los casos manualmente.", "Las intervenciones pueden ocurrir tarde.",
         "Es difícil evaluar el seguimiento realizado."]
TO_BE = ["Los datos se integran desde fuentes configuradas (ETL).", "El sistema valida y calcula indicadores.",
         "Se generan alertas con criterios verificables.", "Una persona revisa y asigna la intervención.",
         "Se registra y evalúa la evolución del caso.", "La dirección consulta resultados y documenta decisiones."]

# ------------------------------------------------------------------ alineación (sección 10 del catálogo)
with t_ali:
    st.markdown("El proceso no termina cuando el sistema genera una alerta: termina cuando la institución registra "
                "una acción, la evalúa y usa el resultado para mejorar la siguiente decisión.")
    head = "".join(f"<th>{h}</th>" for h in ("Etapa del proceso TO-BE", "Funcionalidades", "Tecnología",
                                             "Decisión o resultado", "Dónde se ve"))
    body = "".join(f"<tr><td><b>{i}. {common.esc(e)}</b></td><td>{f}</td><td>{common.esc(t)}</td>"
                   f"<td>{common.esc(d)}</td><td>{common.esc(w)}</td></tr>"
                   for i, (e, f, t, d, w) in enumerate(MATRIZ, 1))
    st.markdown("<div class='edu-heat edu-matrix'><table><thead><tr>" + head + "</tr></thead><tbody>" + body +
                "</tbody></table></div>", unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Proceso actual (AS-IS)")
        common.note("Escenario hipotético de referencia.")
        st.markdown("<ol class='edu-flowlist'>" + "".join(f"<li>{common.esc(x)}</li>" for x in AS_IS) + "</ol>",
                    unsafe_allow_html=True)
    with b:
        st.markdown("#### Proceso mejorado (TO-BE)")
        common.note("Lo que este sistema implementa.")
        st.markdown("<ol class='edu-flowlist tobe'>" + "".join(f"<li>{common.esc(x)}</li>" for x in TO_BE) +
                    "</ol>", unsafe_allow_html=True)

GROUPS = [
    ("Alerta prioritaria", "Basta con cumplir un criterio.", [
        ("alertas.prioritario.asistencia_min", "Asistencia menor a (%)"),
        ("alertas.prioritario.promedio_min", "Promedio menor a"),
        ("alertas.prioritario.ausencias_consecutivas", "Ausencias consecutivas desde")]),
    ("Alerta preventiva", "Señales de atención sin llegar a lo crítico.", [
        ("alertas.preventivo.asistencia_min", "Asistencia menor a (%)"),
        ("alertas.preventivo.promedio_min", "Promedio menor a"),
        ("alertas.preventivo.ausencias_consecutivas", "Ausencias consecutivas desde")]),
    ("Calificaciones", "", [("alertas.nota_aprobacion", "Nota mínima aprobatoria")]),
    ("Necesidad tecnológica", "", [
        ("tecnologia.dispositivos_por_estudiante_critico", "Disp./estudiante crítico (menor a)"),
        ("tecnologia.dispositivos_por_estudiante_minimo", "Disp./estudiante mínimo (menor a)"),
        ("tecnologia.velocidad_minima_mbps", "Velocidad mínima (Mbps)")]),
    ("Recomendaciones", "Cuándo el motor sugiere una acción a la dirección.", [
        ("recomendaciones.pct_prioritarios_centro", "% prioritarios en un centro desde"),
        ("recomendaciones.alertas_sin_seguimiento_max", "Alertas prioritarias sin caso desde"),
        ("recomendaciones.brecha_asistencia_region", "Brecha regional de asistencia (pts)"),
        ("recomendaciones.caida_asistencia_centro", "Caída de asistencia en centro (pts)")]),
    ("Automatización", "", [("pipeline.intervalo_minutos", "Frecuencia del pipeline (minutos)")]),
]

# Rango válido de cada regla: evita, por ejemplo, una asistencia mínima negativa que apagaría las alertas.
LIMITES = {
    "alertas.prioritario.asistencia_min": (0, 100), "alertas.preventivo.asistencia_min": (0, 100),
    "alertas.prioritario.promedio_min": (0, 100), "alertas.preventivo.promedio_min": (0, 100),
    "alertas.prioritario.ausencias_consecutivas": (1, 60), "alertas.preventivo.ausencias_consecutivas": (1, 60),
    "alertas.nota_aprobacion": (1, 100),
    "tecnologia.dispositivos_por_estudiante_critico": (0, 5), "tecnologia.dispositivos_por_estudiante_minimo": (0, 5),
    "tecnologia.velocidad_minima_mbps": (0, 1000),
    "recomendaciones.pct_prioritarios_centro": (1, 100), "recomendaciones.alertas_sin_seguimiento_max": (1, 10000),
    "recomendaciones.brecha_asistencia_region": (0, 100), "recomendaciones.caida_asistencia_centro": (0, 100),
    "pipeline.intervalo_minutos": (1, 1440),
}

# ------------------------------------------------------------------ reglas
with t_reg:
    editable = common.can("editar_reglas")
    common.note("Umbrales ilustrativos y configurables del prototipo; no son política oficial de MEDUCA ni un modelo "
                "predictivo validado. Cada cambio queda auditado y recalcula indicadores, alertas y recomendaciones.")
    if not editable:
        st.info("Su perfil puede consultar las reglas; solo el perfil Tecnología las modifica.", icon=":material/lock:")
    rules = sql.get_rules(conn)
    flat = config.flatten(rules)
    new = {}
    with st.form("rules", border=False):
        for title, sub, fields in GROUPS:
            st.markdown(f"#### {title}")
            if sub:
                common.note(sub)
            cols = st.columns(4)
            for i, (k, label) in enumerate(fields):
                v = flat[k]
                step = 0.01 if isinstance(v, float) and v < 1 else 1.0 if isinstance(v, float) else 1
                lo, hi = LIMITES.get(k, (None, None))
                cast = float if isinstance(v, float) else int
                new[k] = cols[i].number_input(label, value=v, step=step, key=f"rule_{k}", disabled=not editable,
                                              min_value=None if lo is None else cast(lo),
                                              max_value=None if hi is None else cast(hi))
        st.write("")
        if st.form_submit_button("Guardar y recalcular", type="primary", disabled=not editable):
            p, v = "alertas.prioritario", "alertas.preventivo"
            if new[f"{p}.asistencia_min"] > new[f"{v}.asistencia_min"] or new[f"{p}.promedio_min"] > new[
                    f"{v}.promedio_min"] or new[f"{p}.ausencias_consecutivas"] < new[f"{v}.ausencias_consecutivas"]:
                st.error("Los umbrales prioritarios deben ser más estrictos que los preventivos.")
            elif new["tecnologia.dispositivos_por_estudiante_critico"] > new["tecnologia.dispositivos_por_estudiante_minimo"]:
                st.error("El umbral crítico de dispositivos por estudiante no puede superar al mínimo.")
            else:
                changed = {k: (flat[k], val) for k, val in new.items() if val != flat[k]}
                for k, (_, val) in changed.items():
                    sql.set_rule(conn, k, val, u["usuario"])
                if changed:
                    audit.log(u["usuario"], "editar_reglas", "configuracion", None,
                              {k: {"antes": a, "despues": b} for k, (a, b) in changed.items()}, u["perfil"])
                    from edualerta.services import alerts, indicators, recommendations
                    r2 = sql.get_rules(conn)
                    indicators.compute_all(conn, r2)
                    d = common.db()
                    if d is not None:
                        alerts.sync_alerts(conn, d, r2)
                        recommendations.generate(conn, d, r2)
                    st.toast(f"{len(changed)} regla(s) actualizada(s) y resultados recalculados.")
                    # El formulario debe volver a dibujarse con los valores guardados: si no, en el siguiente envío
                    # Streamlit no reconoce los campos cuyo valor inicial cambió y descarta lo escrito.
                    st.rerun()
                else:
                    st.toast("No hubo cambios.")
    hist = sql.query_df(conn, "SELECT clave, valor, actualizado_en, actualizado_por FROM configuracion "
                              "WHERE clave NOT LIKE 'estado.%' ORDER BY actualizado_en DESC")
    with st.expander("Valores vigentes y última modificación"):
        hist["actualizado_en"] = pd.to_datetime(hist["actualizado_en"]).dt.strftime("%d/%m/%Y %H:%M")
        common.table(hist.rename(columns={"clave": "Regla", "valor": "Valor", "actualizado_en": "Modificada",
                                          "actualizado_por": "Por"}))

# ------------------------------------------------------------------ perfiles (F72-F73)
with t_perf:
    common.note("Cada perfil ve solo sus pantallas y ejecuta solo sus acciones. El perfil Tecnología no accede al "
                "seguimiento individual de estudiantes y solo Dirección registra decisiones.")
    profs = auth.profiles()
    head = "<th>Pantalla</th>" + "".join(f"<th>{esc(p['nombre'])}</th>" for p in profs.values())
    body = "".join(
        f"<tr><td><b>{esc(lbl)}</b></td>" + "".join(
            f"<td>{'<span style=color:#2F8A5B>✓</span>' if key in p['paginas'] else '<span style=color:#B0B8B4>—</span>'}</td>"
            for p in profs.values()) + "</tr>" for key, lbl in auth.PAGINAS.items())
    st.markdown(f"<div class='edu-heat'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
                unsafe_allow_html=True)
    st.markdown("#### Acciones permitidas")
    cols = st.columns(len(profs), gap="large")
    for col, (key, p) in zip(cols, profs.items()):
        users = [x["nombre"] for x in auth.users() if x["perfil"] == key]
        col.markdown(f"**{esc(p['nombre'])}**  \n<span class='edu-note'>{esc(', '.join(users))}</span>",
                     unsafe_allow_html=True)
        col.markdown("".join(f"{common.soft_chip(a.replace('_', ' '))} " for a in p["acciones"]),
                     unsafe_allow_html=True)

# ------------------------------------------------------------------ auditoría (F75)
with t_aud:
    a, b, _ = st.columns([1, 1, 1.5])
    fu = a.selectbox("Usuario", [None] + [x["usuario"] for x in auth.users()] + ["sistema", "scheduler"],
                     format_func=lambda x: x or "Todos")
    ev = audit.events(1000, usuario=fu)
    acts = sorted(ev["accion"].dropna().unique()) if not ev.empty else []
    fa = b.selectbox("Acción", [None] + acts, format_func=lambda x: "Todas" if not x else x.replace("_", " "))
    if fa:
        ev = ev[ev["accion"] == fa]
    common.note(f"{len(ev)} eventos: quién hizo qué, sobre qué registro y cuándo.")
    if not ev.empty:
        ev = ev.copy()
        ev["fecha"] = pd.to_datetime(ev["fecha"]).dt.strftime("%d/%m/%Y %H:%M:%S")
        ev["accion"] = ev["accion"].str.replace("_", " ")
        common.table(ev, ["fecha", "usuario", "perfil", "accion", "entidad", "entidad_id", "detalle"], max_height=480)
        common.csv_button(common.pretty(ev), "auditoria.csv")

# ------------------------------------------------------------------ gobierno de datos (F74, F76-F78)
with t_gob:
    st.markdown("#### Catálogo de conjuntos de datos")
    src = pd.DataFrame(config.sources())[["nombre", "entidad", "formato", "origen", "naturaleza", "responsable"]]
    meta = sql.query_df(conn, "SELECT nombre, registros FROM fuentes")
    common.table(src.merge(meta, on="nombre", how="left"),
                 rename={"nombre": "Fuente", "formato": "Formato", "naturaleza": "Naturaleza"})
    st.markdown("#### Calidad de datos")
    q = quality.by_source(conn)
    if not q.empty:
        common.table(q, ["fuente", "leidos", "aceptados", "rechazados", "completitud_pct", "consistencia_pct",
                         "apto_para_decidir"])
        if not q["apto_para_decidir"].all():
            st.warning("Alguna fuente está por debajo del 95 % de completitud o consistencia: no debería usarse para "
                       "decidir hasta corregirla (respuesta al riesgo R1).", icon=":material/warning:")
    st.markdown("#### Matriz de riesgos y controles")
    rm = pd.DataFrame(config.risk_matrix())
    rm["nivel"] = [risk_level(p, i) for p, i in zip(rm["probabilidad"], rm["impacto"])]
    d = common.db()
    linked = {}
    if d is not None:
        linked = {x["_id"]: x["n"] for x in d.decisiones.aggregate(
            [{"$unwind": "$riesgos"}, {"$match": {"riesgos.riesgo_matriz": {"$ne": None}}},
             {"$group": {"_id": "$riesgos.riesgo_matriz", "n": {"$sum": 1}}}])}
    rm["decisiones"] = rm["id"].map(lambda x: linked.get(x, 0))
    common.table(rm, ["id", "categoria", "riesgo", "consecuencia", "probabilidad", "impacto", "nivel", "responsable",
                      "preventivo", "respuesta", "decisiones"],
                 rename={"id": "ID", "categoria": "Categoría", "riesgo": "Riesgo", "nivel": "Nivel de riesgo",
                         "preventivo": "Medida preventiva", "respuesta": "Respuesta",
                         "decisiones": "Decisiones vinculadas"},
                 color_cols={"Nivel de riesgo": {"bajo": common.GREEN, "medio": common.AMBER, "alto": common.RED}})
    st.markdown("#### Privacidad")
    n_real = conn.execute("SELECT COUNT(*) FROM estudiantes WHERE sintetico=0").fetchone()[0]
    items = ["Los estudiantes se identifican solo con un código anónimo (E-NNNN): sin nombres ni cédulas.",
             f"Registros no sintéticos en la base: {n_real}.",
             "MongoDB vincula los documentos únicamente por el código anónimo.",
             "El perfil Tecnología no accede al seguimiento individual."]
    st.markdown("<ul class='edu-reasons'>" + "".join(f"<li><span>{esc(x)}</span></li>" for x in items) + "</ul>",
                unsafe_allow_html=True)

# ------------------------------------------------------------------ automatización (F79-F85)
with t_auto:
    can_admin = common.can("restablecer_demo")
    rules = sql.get_rules(conn)
    nxt = rules.get("estado", {}).get("scheduler_proxima_ejecucion")
    last = conn.execute("SELECT id, fin, estado FROM ejecuciones_etl WHERE disparador LIKE 'programado%' "
                        "ORDER BY id DESC LIMIT 1").fetchone()
    common.kpi_band([
        {"label": "Frecuencia programada", "value": rules["pipeline"]["intervalo_minutos"], "unit": "min"},
        {"label": "Próxima ejecución", "value": pd.to_datetime(nxt).strftime("%H:%M") if nxt else "inactivo",
         "delta": pd.to_datetime(nxt).strftime("%d/%m/%Y") if nxt else "el contenedor scheduler no responde"},
        {"label": "Última ejecución programada", "value": f"n.º {last['id']}" if last else "—",
         "delta": last["estado"].replace("_", " ") if last else None},
    ])
    common.note("El contenedor scheduler relee la frecuencia en cada ciclo; se cambia en la pestaña Reglas.")
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Simular ejecución programada")
        common.note("Ejecuta el pipeline como lo haría el scheduler. Los archivos ya procesados se omiten.")
        if st.button("Simular ahora", icon=":material/schedule:", disabled=not can_admin):
            out = pipeline.run(trigger="programado_simulado", usuario=u["usuario"], perfil=u["perfil"])
            st.toast(f"Ejecución n.º {out.get('id')}: {out['estado']}, {out['omitidos']} archivos omitidos.")
            st.rerun()  # actualiza el encabezado («Datos al…») y los indicadores de esta pestaña
    with b:
        st.markdown("#### Restablecer la demostración")
        common.note("Borra SQL, MongoDB y archivos subidos, y recarga la carga base 2025.")
        with st.popover("Restablecer escenario", disabled=not can_admin, icon=":material/restart_alt:"):
            st.warning("Se perderán casos, intervenciones y decisiones registrados.")
            if st.button("Sí, restablecer", type="primary"):
                from edualerta import cli
                with st.spinner("Restableciendo…"):
                    cli.reset(usuario=u["usuario"], perfil=u["perfil"])
                st.session_state.pop("last_run", None)
                st.toast("Escenario inicial restablecido.")
                st.rerun()
    st.markdown("#### Pruebas automáticas")
    common.note("Ejecuta Pytest dentro del contenedor contra bases de prueba aisladas; no toca los datos de la demo.")
    if st.button("Ejecutar pruebas", icon=":material/science:", disabled=not can_admin):
        env = {**os.environ, "MONGO_DB": "edualerta_uitest", "SQLITE_PATH": "/tmp/edualerta_uitest.db"}
        with st.spinner("Ejecutando pytest…"):
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
                                  cwd=str(config.BASE_DIR), capture_output=True, text=True, env=env, timeout=600)
        audit.log(u["usuario"], "ejecutar_pruebas", "sistema", None, {"codigo_salida": proc.returncode}, u["perfil"])
        (st.success if proc.returncode == 0 else st.error)(
            "Todas las pruebas pasaron." if proc.returncode == 0 else "Hay pruebas fallidas.")
        st.code(proc.stdout[-6000:] + proc.stderr[-2000:])

# ------------------------------------------------------------------ estado
with t_sys:
    ok = mongo.ping()
    common.kpi_band([
        {"label": "SQLite", "value": "conectado", "good": True, "delta": str(config.sqlite_path())},
        {"label": "MongoDB", "value": "conectado" if ok else "sin conexión", "good": ok,
         "delta": config.mongo_uri().split("@")[-1]},
    ])
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Registros por tabla SQL")
        common.table(pd.DataFrame(sql.table_counts(conn).items(), columns=["Tabla", "Registros"]))
    with b:
        if ok:
            d = mongo.get_db()
            st.markdown("#### Documentos por colección MongoDB")
            common.table(pd.DataFrame([(c, d[c].count_documents({})) for c in mongo.COLLECTIONS],
                                      columns=["Colección", "Documentos"]))
