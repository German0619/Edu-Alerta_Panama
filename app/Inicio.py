"""Punto de entrada de EDU-ALERTA Panamá (Streamlit). Enruta las 8 pantallas según el perfil."""
from __future__ import annotations

import common  # noqa: F401  (ajusta sys.path)
import streamlit as st

from common import CSS, esc, persist_filters
from edualerta.config import demo_password
from edualerta.services import audit, auth

st.set_page_config(page_title="EDU-ALERTA Panamá", page_icon=":material/school:", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
persist_filters()

LOGIN_CSS = """
<style>
.block-container { max-width: 1100px; padding-top: 4rem; }
.edu-login-brand { background: #183A34; border-radius: 12px; padding: 2.2rem 2.2rem 2rem; color: #E8EFEB; }
.edu-login-brand * { color: #E8EFEB !important; }
.edu-login-brand .name { font-family: 'Bricolage Grotesque', sans-serif !important; font-size: 2.6rem;
    font-weight: 800; letter-spacing: -0.03em; line-height: 1; color: #fff !important; }
.edu-login-brand .tag { margin: .8rem 0 1.6rem; font-size: 1.05rem; color: #BFD1C9 !important; max-width: 36ch; }
.edu-flow { list-style: none; padding: 0; margin: 0; counter-reset: paso; }
.edu-flow li { counter-increment: paso; display: grid; grid-template-columns: 1.8rem 1fr; gap: .6rem;
    padding: .45rem 0; border-top: 1px solid rgba(255,255,255,.12); font-size: .95rem; }
.edu-flow li::before { content: counter(paso); font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
    color: #9CC7F0; }
.edu-login-note { margin-top: 1.4rem; font-size: .85rem; color: #A9C3B9 !important; }
.edu-roles { margin-top: .4rem; }
.edu-roles div { display: grid; grid-template-columns: 1fr auto; padding: .55rem 0;
    border-bottom: 1px solid #D9E0DC; font-size: .92rem; }
.edu-roles span { color: #5E6B66; }
</style>
"""

ICONS = {"inicio": ":material/space_dashboard:", "datos": ":material/database:",
         "seguimiento": ":material/person_alert:", "tecnologia": ":material/devices:",
         "regiones": ":material/map:", "analisis": ":material/monitoring:",
         "decisiones": ":material/gavel:", "administracion": ":material/admin_panel_settings:"}


def login_page():
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("""
<div class="edu-login-brand">
  <div class="name">EDU-ALERTA<br>Panamá</div>
  <p class="tag">Detecta a tiempo a los estudiantes que necesitan apoyo y deja constancia de cada acción.</p>
  <ol class="edu-flow">
    <li>Integra asistencia, notas y recursos de cada centro</li>
    <li>Señala casos con motivos verificables</li>
    <li>Una persona revisa, confirma y asigna responsable</li>
    <li>Se registra la intervención y se mide su efecto</li>
    <li>La dirección decide y evalúa los riesgos</li>
  </ol>
  <p class="edu-login-note">Prototipo con datos sintéticos. Las alertas son señales basadas en reglas, no predicciones.</p>
</div>""", unsafe_allow_html=True)
    with right:
        st.markdown("## Ingresar")
        with st.form("login", border=False):
            users = auth.users()
            labels = {u["usuario"]: u["nombre"] for u in users}
            usuario = st.selectbox("Usuario", list(labels), format_func=labels.get)
            password = st.text_input("Contraseña", type="password")
            ok = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            if ok:
                u = auth.authenticate(usuario, password)
                if u:
                    st.session_state["user"] = u
                    audit.log(u["usuario"], "iniciar_sesion", "sesion", None, {}, u["perfil"])
                    st.rerun()
                else:
                    audit.log(usuario, "inicio_sesion_fallido", "sesion", None, {})
                    st.error("La contraseña no coincide. Use la contraseña de demostración.")
        if demo_password() == "edualerta":
            common.note("Contraseña de demostración: <b>edualerta</b>")
        rows = "".join(f'<div><b>{esc(u["nombre"])}</b><span>{esc(auth.profiles()[u["perfil"]]["nombre"])}</span></div>'
                       for u in auth.users())
        st.markdown(f'<div class="edu-roles">{rows}</div>', unsafe_allow_html=True)


def logout():
    u = st.session_state.pop("user", None)
    if u:
        audit.log(u["usuario"], "cerrar_sesion", "sesion", None, {}, u["perfil"])


user = st.session_state.get("user")
if not user:
    st.navigation([st.Page(login_page, title="Ingreso", icon=":material/login:")], position="hidden").run()
else:
    files = {"inicio": "inicio", "datos": "datos", "seguimiento": "seguimiento", "tecnologia": "tecnologia",
             "regiones": "regiones", "analisis": "analisis", "decisiones": "decisiones",
             "administracion": "administracion"}
    defs = {k: st.Page(f"views/{files[k]}.py", title=auth.PAGINAS[k], icon=ICONS[k], default=(k == "inicio"))
            for k in files}
    pages = [p for k, p in defs.items() if k in user["paginas"]]
    nav = st.navigation(pages)
    with st.sidebar:
        initials = "".join(p[0] for p in user["nombre"].split()[:2])
        st.markdown(f'<div class="edu-user"><div class="av">{esc(initials)}</div><div>'
                    f'<div class="nm">{esc(user["nombre"])}</div><div class="rl">{esc(user["cargo"])}</div>'
                    f'</div></div>', unsafe_allow_html=True)
        st.button("Cerrar sesión", on_click=logout, icon=":material/logout:", use_container_width=True)
        st.divider()
    nav.run()
