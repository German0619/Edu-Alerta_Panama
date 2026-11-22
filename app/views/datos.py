"""Pantalla 2 · Datos y ETL (F01-F22, F77, F79, F81)."""
import json
from datetime import date

import pandas as pd
import streamlit as st

import common
from edualerta import config
from edualerta.db import sql
from edualerta.etl import extract, pipeline
from edualerta.services import audit, masters, quality

u = common.guard("datos")
conn = common.conn()
can_load, can_run = common.can("cargar_archivos"), common.can("ejecutar_etl")

common.header("Datos y ETL",
              "De dónde vienen los datos, cómo se limpian y validan, y si son confiables para decidir.")

t_flow, t_log, t_cal, t_maes, t_src = st.tabs(
    ["Cargar y procesar", "Bitácora", "Calidad y rechazos", "Centros y estudiantes", "Fuentes"])
sources = {s["nombre"]: s for s in config.sources()}
TABLAS = {"regiones": "Regiones", "centros": "Centros", "periodos": "Períodos", "estudiantes": "Estudiantes",
          "matriculas": "Matrículas", "asistencias": "Asistencias", "calificaciones": "Calificaciones",
          "recursos_tecnologicos": "Inventario tecnológico", "indicadores": "Indicadores",
          "ejecuciones_etl": "Ejecuciones ETL", "rechazos_etl": "Registros rechazados"}

# ------------------------------------------------------------------ carga + ejecución (F07-F22, F79, F81)
with t_flow:
    pend = []
    for name, s in sources.items():
        for p in extract.discover(s):
            if not conn.execute("SELECT 1 FROM archivos_procesados WHERE sha256=?", (extract.file_hash(p),)).fetchone():
                pend.append({"fuente": name, "archivo": p.name,
                             "origen": "carga base" if p.parent == config.RAW_DIR else "subido por la interfaz"})
    l, r = st.columns([1.15, 1], gap="large")
    with l:
        common.step(1, "Cargar fuentes", "CSV, JSON o GeoJSON. Se revisa la estructura antes de aceptarlo.")
        if not can_load:
            common.empty("Solo el perfil Tecnología carga archivos.", "Usted puede consultar las fuentes y su calidad.")
        else:
            up = st.file_uploader("Archivo de datos", type=["csv", "json", "geojson"], label_visibility="collapsed")
            if up is not None:
                data = up.getvalue()
                guess = extract.detect_source(up.name)
                names = list(sources)
                fuente = st.selectbox("Fuente de destino", names, index=names.index(guess["nombre"]) if guess else 0,
                                      format_func=lambda n: f"{n} ({sources[n]['formato'].upper()})")
                src = sources[fuente]
                try:
                    pv = extract.preview(data, src)
                except extract.SourceError as exc:
                    st.error(f"No se puede leer el archivo: {exc}")
                    pv = None
                if pv:
                    common.facts([{"k": "Registros", "v": pv["registros"]},
                                  {"k": "Columnas", "v": len(pv["columnas_originales"])},
                                  {"k": "Estructura", "v": "Completa" if pv["valido"] else "Incompleta",
                                   "d": None if pv["valido"] else f"faltan: {', '.join(pv['faltantes'])}",
                                   "good": pv["valido"]}])
                    common.table(pv["muestra"], max_height=250)
                    common.note(f"Vista previa con encabezados normalizados. {common.esc(src['descripcion'])}")
                    if st.button("Agregar a la cola de procesamiento", type="primary", disabled=not pv["valido"],
                                 icon=":material/playlist_add:"):
                        path = pipeline.save_upload(fuente, up.name, data)
                        audit.log(u["usuario"], "cargar_archivo", "fuentes", fuente,
                                  {"archivo": up.name, "registros": pv["registros"], "formato": src["formato"]},
                                  u["perfil"])
                        st.toast(f"{path.name} quedó en la cola.")
                        st.rerun()
            st.markdown("**¿Sin archivos a mano?** El paquete de demostración 2026-T1 simula la entrega de un nuevo "
                        "trimestre (incluye a propósito una fecha y una nota inválidas).")
            if st.button("Agregar paquete de demostración 2026-T1", icon=":material/inventory_2:"):
                files = pipeline.stage_demo_package()
                audit.log(u["usuario"], "cargar_paquete_demo", "fuentes", "2026-T1", {"archivos": files}, u["perfil"])
                st.toast(f"{len(files)} archivos en la cola.")
                st.rerun()
    with r:
        common.step(2, "Procesar", "Extraer, limpiar, validar, cargar en SQL y MongoDB, calcular indicadores y "
                                   "alertas.", "" if pend else "done")
        st.markdown(f"**Cola: {len(pend)} archivo{'s' if len(pend) != 1 else ''} pendiente{'s' if len(pend) != 1 else ''}**")
        if pend:
            common.table(pd.DataFrame(pend), max_height=220)
        else:
            common.note("Todo lo disponible ya fue procesado. Re-ejecutar no duplica registros: los archivos se "
                        "reconocen por su huella SHA-256 y la carga actualiza en lugar de insertar.")
        force = st.checkbox("Reprocesar también lo ya cargado (prueba de idempotencia)", disabled=not can_run)
        if st.button("Ejecutar pipeline", type="primary", icon=":material/play_arrow:", disabled=not can_run,
                     use_container_width=True):
            with st.status("Ejecutando pipeline…", expanded=True) as status:
                before = sql.table_counts(conn)
                out = pipeline.run(trigger="manual", usuario=u["usuario"], force=force, perfil=u["perfil"])
                after = sql.table_counts(conn)
                for p in out.get("pasos", []):
                    st.write(("✓ " if p["estado"] == "ok" else "✗ ") + f"{p['paso']} ({p['segundos']} s)")
                status.update(label=f"Ejecución n.º {out.get('id')}: {out['estado'].replace('_', ' ')}",
                              state="error" if out["estado"] == "fallida" else "complete", expanded=False)
            st.session_state["last_run"] = {"out": out, "before": before, "after": after}
            st.rerun()  # el encabezado y la cola se dibujaron antes de ejecutar: se actualizan con la nueva corrida
        if not can_run:
            common.note("La ejecución manual está reservada al perfil Tecnología.")
        lr = st.session_state.get("last_run")
        if lr:
            out = lr["out"]
            failed = out["estado"] == "fallida"
            with st.expander(f"Ejecución n.º {out.get('id')}: {out['estado'].replace('_', ' ')}",
                             icon=":material/error:" if failed else ":material/check_circle:"):
                for p in out.get("pasos", []):
                    st.write(("✓ " if p["estado"] == "ok" else "✗ ") + f"{p['paso']} ({p['segundos']} s)")
            common.facts([{"k": "Leídos", "v": f"{out.get('leidos', 0):,}".replace(",", " ")},
                          {"k": "Aceptados", "v": f"{out.get('aceptados', 0):,}".replace(",", " ")},
                          {"k": "Rechazados", "v": out.get("rechazados", 0), "good": False if out.get("rechazados") else None},
                          {"k": "Omitidos (ya procesados)", "v": out.get("omitidos", 0)}])
            diff = pd.DataFrame({"tabla": [TABLAS[t] for t in lr["after"]], "antes": list(lr["before"].values()),
                                 "después": list(lr["after"].values())})
            diff["variación"] = diff["después"] - diff["antes"]
            common.table(diff.rename(columns={"tabla": "Tabla", "antes": "Antes", "después": "Después",
                                              "variación": "Variación"}))
            for e in out.get("errores", []):
                st.warning(e, icon=":material/warning:")

# ------------------------------------------------------------------ bitácora (F21)
with t_log:
    runs = sql.query_df(conn, "SELECT id, inicio, fin, estado, disparador, usuario, leidos, aceptados, rechazados, "
                              "omitidos, pasos, errores FROM ejecuciones_etl ORDER BY id DESC LIMIT 100")
    if runs.empty:
        common.empty("Sin ejecuciones registradas.")
    else:
        rv = runs.copy()
        rv["inicio"] = pd.to_datetime(rv["inicio"]).dt.strftime("%d/%m/%Y %H:%M:%S")
        rv["estado"] = rv["estado"].str.replace("_", " ")
        ev = common.table(rv, ["id", "inicio", "estado", "disparador", "usuario", "leidos", "aceptados",
                               "rechazados", "omitidos"], max_height=300, on_select="rerun",
                          selection_mode="single-row", key="runs_tab",
                          color_cols={"Estado": {"exitosa": common.GREEN, "con advertencias": common.AMBER,
                                                 "fallida": common.RED}})
        idx = ev.selection.rows[0] if ev.selection.rows else 0
        row = runs.iloc[idx]
        st.markdown(f"#### Pasos de la ejecución n.º {row['id']}")
        steps = pd.DataFrame(json.loads(row["pasos"] or "[]"))
        if not steps.empty:
            steps["detalle"] = steps["detalle"].map(
                lambda d: ", ".join(f"{k}: {v}" for k, v in d.items() if k not in ("errores", "fuente"))
                if isinstance(d, dict) else d)
            common.table(steps.rename(columns={"paso": "Paso", "segundos": "Segundos"}),
                         color_cols={"Estado": {"ok": common.GREEN, "error": common.RED}})
        for e in json.loads(row["errores"] or "[]"):
            st.warning(e, icon=":material/warning:")
        common.csv_button(common.pretty(runs.drop(columns=["pasos"])), "bitacora_etl.csv")

# ------------------------------------------------------------------ calidad (F15, F17, F77)
with t_cal:
    q = quality.by_source(conn)
    if q.empty:
        common.empty("Sin datos de calidad todavía.")
    else:
        tot_l, tot_r = int(q["leidos"].sum()), int(q["rechazados"].sum())
        apto = bool(q["apto_para_decidir"].all())
        common.kpi_band([
            {"label": "Registros leídos", "value": f"{tot_l:,}".replace(",", " ")},
            {"label": "Registros rechazados", "value": tot_r, "delta": f"{tot_r / tot_l * 100:.3f} % del total"},
            {"label": "Completitud mínima", "value": f"{q['completitud_pct'].min():.2f}", "unit": "%"},
            {"label": "Consistencia mínima", "value": f"{q['consistencia_pct'].min():.2f}", "unit": "%"},
            {"label": "Información", "value": "Apta" if apto else "Revisar", "good": apto,
             "delta": "para decidir (umbral 95 %)"},
        ])
        common.table(q, ["fuente", "archivos", "leidos", "aceptados", "rechazados", "incompletos", "duplicados",
                         "inconsistentes", "completitud_pct", "consistencia_pct", "apto_para_decidir"])
        common.note("Completitud = 1 − registros con campos obligatorios vacíos ÷ leídos. Consistencia = 1 − registros "
                    "que violan una regla de negocio ÷ leídos.")
        l, r = st.columns([1.3, 1], gap="large")
        with l:
            st.markdown("#### Motivos de rechazo")
            common.table(quality.reject_reasons(conn))
        with r:
            st.markdown("#### Cobertura de indicadores")
            common.table(quality.coverage(conn), rename={"matriculados": "Matriculados"})
        st.markdown("#### Registros rechazados")
        rj = quality.rejects(conn)
        common.table(rj, ["ejecucion_id", "fuente", "archivo", "fila", "motivo", "datos"],
                     rename={"ejecucion_id": "Ejecución"}, max_height=300)
        common.csv_button(common.pretty(rj), "registros_rechazados.csv")

# ------------------------------------------------------------------ maestros (F01-F06)
with t_maes:
    edit = common.can("gestionar_maestros")
    sub = st.segmented_control("Vista", ["Centros", "Estudiantes y matrícula", "Períodos", "Integridad"],
                               default="Centros", key="m_sub", label_visibility="collapsed") or "Centros"
    reg = sql.query_df(conn, "SELECT codigo, nombre FROM regiones ORDER BY nombre")
    reg_map = dict(zip(reg["codigo"], reg["nombre"]))
    if sub == "Centros":
        cf = masters.centers_frame(conn)
        a, _ = st.columns([1, 2])
        rsel = a.multiselect("Región", list(reg_map), format_func=reg_map.get, placeholder="Todas", key="m_creg")
        common.table(cf[cf["region_codigo"].isin(rsel)] if rsel else cf,
                     ["codigo", "nombre", "region_nombre", "zona", "dependencia", "nivel", "estudiantes"],
                     rename={"nivel": "Nivel educativo"})
        if edit:
            with st.expander("Registrar centro educativo"):
                with st.form("f_centro", clear_on_submit=True):
                    a, b = st.columns(2)
                    # El valor inicial debe ser fijo: si cambiara tras cada alta, Streamlit trataría el campo como
                    # uno nuevo al enviar y descartaría lo escrito. El código sugerido va como placeholder.
                    sugerido = masters.next_center_code(conn)
                    codigo = a.text_input("Código", placeholder=f"{sugerido} (si se deja vacío)") or sugerido
                    nombre = b.text_input("Nombre")
                    region = a.selectbox("Región", list(reg_map), format_func=reg_map.get)
                    zona = b.selectbox("Zona", ["urbana", "rural"])
                    dep = a.selectbox("Dependencia", ["oficial", "particular"])
                    nivel = b.selectbox("Nivel", ["premedia", "media", "primaria"])
                    if st.form_submit_button("Guardar centro", type="primary"):
                        try:
                            masters.save(conn, "centros", {"codigo": codigo, "nombre": nombre, "region_codigo": region,
                                                           "zona": zona, "dependencia": dep, "nivel": nivel},
                                         u["usuario"], u["perfil"])
                            st.toast("Centro registrado.")
                        except ValueError as exc:
                            st.error(str(exc))
    elif sub == "Estudiantes y matrícula":
        per_all = sql.all_periods(conn)
        cen = sql.query_df(conn, "SELECT codigo, nombre FROM centros ORDER BY codigo")
        cen_map = dict(zip(cen["codigo"], cen["codigo"] + " " + cen["nombre"].str.replace("Centro Educativo ", "")))
        a, b, c, d = st.columns(4)
        fp = a.selectbox("Período", [None] + per_all[::-1], format_func=lambda x: x or "Todos")
        fr = b.multiselect("Región", list(reg_map), format_func=reg_map.get, key="m_reg", placeholder="Todas")
        fc = c.multiselect("Centro", list(cen_map), format_func=cen_map.get, key="m_cen", placeholder="Todos")
        fg = d.multiselect("Grado", list(range(1, 13)), key="m_gr", placeholder="Todos")
        sf = masters.students_frame(conn, fp, fr, fc, fg)
        common.note(f"{sf['codigo'].nunique()} estudiantes · {len(sf)} matrículas")
        common.table(sf, ["codigo", "genero", "anio_nacimiento", "periodo_codigo", "grado", "estado_matricula",
                          "centro_codigo", "centro", "region"], max_height=380)
        common.csv_button(common.pretty(sf), "estudiantes_matriculas.csv")
        if edit:
            e1, e2 = st.columns(2, gap="large")
            with e1.expander("Registrar estudiante ficticio"):
                with st.form("f_est", clear_on_submit=True):
                    sugerido = masters.next_student_code(conn)
                    codigo = st.text_input("Código anónimo", placeholder=f"{sugerido} (si se deja vacío)") or sugerido
                    a, b = st.columns(2)
                    genero = a.selectbox("Género", ["F", "M"])
                    anio = b.number_input("Año de nacimiento", 1995, 2020, 2011)
                    if st.form_submit_button("Guardar estudiante", type="primary"):
                        try:
                            masters.save(conn, "estudiantes", {"codigo": codigo, "genero": genero,
                                                               "anio_nacimiento": anio}, u["usuario"], u["perfil"])
                            st.toast("Estudiante registrado (sin datos personales).")
                        except ValueError as exc:
                            st.error(str(exc))
            with e2.expander("Matricular estudiante"):
                with st.form("f_mat", clear_on_submit=True):
                    a, b = st.columns(2)
                    est = a.text_input("Código del estudiante", "E-")
                    grado = b.number_input("Grado", 1, 12, 7)
                    centro = st.selectbox("Centro", list(cen_map), format_func=cen_map.get)
                    per = st.selectbox("Período", per_all[::-1])
                    if st.form_submit_button("Guardar matrícula", type="primary"):
                        try:
                            masters.save(conn, "matriculas", {"estudiante_codigo": est, "centro_codigo": centro,
                                                              "periodo_codigo": per, "grado": grado,
                                                              "estado": "activa"}, u["usuario"], u["perfil"])
                            st.toast("Matrícula registrada.")
                        except ValueError as exc:
                            st.error(str(exc))
    elif sub == "Períodos":
        pdf_ = sql.query_df(conn, "SELECT * FROM periodos ORDER BY anio, trimestre")
        for c in ("fecha_inicio", "fecha_fin"):
            pdf_[c] = pdf_[c].map(common.fmt_date)
        common.table(pdf_.rename(columns={"anio": "Año", "trimestre": "Trimestre", "fecha_inicio": "Inicio",
                                          "fecha_fin": "Fin"}))
        if edit:
            with st.expander("Registrar período académico"):
                with st.form("f_per"):
                    a, b = st.columns(2)
                    anio = a.number_input("Año", 2020, 2035, date.today().year)
                    tri = b.selectbox("Trimestre", [1, 2, 3])
                    # Sin valor inicial dinámico (ver nota del formulario de centros): vacías = fechas sugeridas.
                    ini = a.date_input("Inicio", None, format="DD/MM/YYYY")
                    fin = b.date_input("Fin", None, format="DD/MM/YYYY")
                    common.note("Si deja las fechas vacías se usa el calendario sugerido para ese trimestre.")
                    if st.form_submit_button("Guardar período", type="primary"):
                        di, df_ = masters.default_period_dates(int(anio), int(tri))
                        ini, fin = ini or di, fin or df_
                        try:
                            masters.save(conn, "periodos", {"codigo": f"{anio}-T{tri}", "anio": anio, "trimestre": tri,
                                                            "fecha_inicio": ini.isoformat(),
                                                            "fecha_fin": fin.isoformat()}, u["usuario"], u["perfil"])
                            st.toast("Período registrado.")
                        except ValueError as exc:
                            st.error(str(exc))
    else:
        rep = masters.integrity_report(conn)
        common.table(rep.rename(columns={"verificación": "Verificación", "registros": "Registros",
                                         "resultado": "Resultado"}),
                     color_cols={"Resultado": {"OK": common.GREEN, "Revisar": common.RED}})
        common.note("Además, el esquema SQL impone claves primarias, foráneas, UNIQUE y CHECK.")

# ------------------------------------------------------------------ fuentes (F13, F76)
with t_src:
    fdf = sql.query_df(conn, "SELECT * FROM fuentes ORDER BY nombre")
    fdf["ultima_carga"] = fdf["ultima_carga"].map(common.fmt_date)
    common.table(fdf, ["nombre", "formato", "naturaleza", "origen", "responsable", "ultima_carga", "registros",
                       "archivos"], rename={"nombre": "Fuente", "formato": "Formato", "naturaleza": "Naturaleza",
                                            "ultima_carga": "Última carga"})
    st.markdown("#### Archivos procesados")
    files = sql.query_df(conn, "SELECT fuente, archivo, registros, aceptados, rechazados, ejecucion_id, procesado_en, "
                               "substr(sha256,1,12) AS huella FROM archivos_procesados ORDER BY procesado_en DESC")
    files["procesado_en"] = pd.to_datetime(files["procesado_en"]).dt.strftime("%d/%m/%Y %H:%M")
    common.table(files, rename={"ejecucion_id": "Ejecución", "procesado_en": "Procesado", "huella": "Huella SHA-256"})
