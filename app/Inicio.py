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


# Barra superior: franja pizarra fija. La página activa se marca con un trazo de tiza.
NAV_LABELS = {**auth.PAGINAS, "tecnologia": "Tecnología"}
CHALK_STROKE = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 8' "
                "preserveAspectRatio='none'%3E%3Cpath d='M2 5.4C18 3.1 31 6.3 49 4.6S82 3 98 4.9' fill='none' "
                "stroke='%239CC7F0' stroke-width='2.4' stroke-linecap='round'/%3E%3C/svg%3E\")")
NAV_CSS = """
<style>
header[data-testid="stHeader"] { display: none; }
.block-container { padding-top: 0; }
/* los bloques que solo inyectan estilos no ocupan espacio (la barra queda pegada al borde superior) */
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child) { display: none; }
.st-key-edu_nav [data-testid="stColumn"]:first-child,
.st-key-edu_nav [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; width: auto !important;
    min-width: 0; }
.st-key-edu_nav [data-testid="stColumn"]:nth-child(2) { flex: 1 1 0 !important; width: auto !important;
    min-width: 0; }
.st-key-edu_nav [data-testid="stColumn"]:first-child div { width: auto !important; }
/* celular: marca y usuario en una fila; los enlaces debajo, deslizables */
@media (max-width: 640px) {
  .st-key-edu_nav [data-testid="stHorizontalBlock"] { flex-wrap: wrap; row-gap: .55rem; }
  .st-key-edu_nav [data-testid="stColumn"]:first-child { flex: 1 1 0 !important; }
  .st-key-edu_nav [data-testid="stColumn"]:nth-child(2) { order: 3; flex: 1 1 100% !important; }
  .st-key-edu_links [data-testid="stPageLink-NavLink"] { padding-left: .42rem; padding-right: .42rem; }
  .st-key-edu_links > div:has(.st-key-nav_administracion) { margin-left: .5rem; }
  .st-key-edu_links > div:has(.st-key-nav_administracion)::before { left: -.3rem; }
}
.st-key-edu_nav { position: sticky; top: 0; z-index: 999; background: #183A34; padding: .55rem 0;
    box-shadow: 0 0 0 100vmax #183A34; clip-path: inset(0 -100vmax); margin-bottom: .6rem;
    /* la barra puede ser más ancha que el contenido (1160 px): con 8 pantallas necesita ~1000 px de enlaces */
    width: min(calc(100vw - 2rem), 1320px) !important; margin-left: calc((100% - min(calc(100vw - 2rem), 1320px)) / 2); }
.edu-mark { font-family: 'Bricolage Grotesque', sans-serif !important; font-weight: 800; font-size: 1.2rem;
    letter-spacing: -.02em; line-height: 1; color: #fff; white-space: nowrap; }
.edu-mark span { display: block; font-weight: 500; font-size: .76rem; letter-spacing: .01em; color: #A9C3B9;
    margin-top: .22rem; }
.st-key-edu_links { flex-direction: row !important; flex-wrap: nowrap; align-items: center; gap: .1rem !important;
    overflow-x: auto; scrollbar-width: none; }
.st-key-edu_links::-webkit-scrollbar { display: none; }
.st-key-edu_links > div { flex: none; }
/* Streamlit fija anchos medidos en px; aquí cada enlace mide lo que su contenido */
.st-key-edu_links div { width: auto !important; }
.st-key-edu_links [data-testid="stPageLink-NavLink"] { padding: .5rem .6rem .65rem; margin: 0; border-radius: 6px;
    background: transparent !important; }
.st-key-edu_links [data-testid="stPageLink-NavLink"]:hover { background-color: rgba(255,255,255,.07) !important; }
.st-key-edu_links [data-testid="stPageLink-NavLink"]:focus-visible { outline: 2px solid #9CC7F0; outline-offset: 0; }
.st-key-edu_links [data-testid="stPageLink-NavLink"] p { color: #CFDCD5; font-size: .93rem; white-space: nowrap; }
.st-key-edu_links [data-testid="stIconMaterial"] { color: #8FB0A4 !important; }
/* Administración es gestión del sistema, no trabajo diario: va separada por un filete */
.st-key-edu_links > div:has(.st-key-nav_administracion) { margin-left: .9rem; position: relative; }
.st-key-edu_links > div:has(.st-key-nav_administracion)::before { content: ""; position: absolute; left: -.5rem;
    top: 22%; bottom: 22%; border-left: 1px solid rgba(255,255,255,.18); }
.st-key-edu_user { align-items: flex-end; }
.st-key-edu_user [data-testid="stPopoverButton"] { background: rgba(255,255,255,.06);
    border-color: rgba(255,255,255,.22); }
.st-key-edu_user [data-testid="stPopoverButton"]:hover { border-color: #9CC7F0; background: rgba(255,255,255,.1); }
.st-key-edu_user [data-testid="stPopoverButton"] :is(p, [data-testid="stIconMaterial"], svg) {
    color: #E8EFEB !important; fill: #E8EFEB; }
/* en anchos medios, solo íconos; la página activa conserva su nombre */
@media (max-width: 1400px) {
  .st-key-edu_links [data-testid="stPageLink-NavLink"] [data-testid="stMarkdownContainer"] {
      max-width: 0; overflow: hidden; }
  .st-key-edu_links [data-testid="stPageLink-NavLink"] { gap: 0; }
}
</style>
"""


def active_css(key: str | None) -> str:
    if not key:
        return ""
    sel = f".st-key-edu_links .st-key-nav_{key} [data-testid='stPageLink-NavLink']"
    return (f"<style>{sel} {{ background: {CHALK_STROKE} no-repeat center bottom .3rem / calc(100% - 1.3rem) 7px"
            f" !important; gap: .5rem !important; }}"
            f"{sel} p {{ color: #fff !important; font-weight: 700; }}"
            f"{sel} [data-testid='stIconMaterial'] {{ color: #9CC7F0 !important; }}"
            f"{sel} [data-testid='stMarkdownContainer'] {{ max-width: none !important; }}</style>")


def masthead(user: dict, keys: list[str], defs: dict, current) -> None:
    active = next((k for k in keys if defs[k].url_path == current.url_path), None)
    with st.container(key="edu_nav"):
        brand, links, who = st.columns([1.2, 6.4, 1.4], vertical_alignment="center", gap="small")
        brand.markdown(NAV_CSS + active_css(active) + '<div class="edu-mark">EDU-ALERTA<span>Panamá</span></div>',
                       unsafe_allow_html=True)
        with links, st.container(key="edu_links"):
            for k in keys:
                with st.container(key=f"nav_{k}"):
                    st.page_link(defs[k], label=NAV_LABELS[k], icon=ICONS[k])
        with who, st.container(key="edu_user"):
            with st.popover(user["nombre"].split()[0], icon=":material/account_circle:"):
                initials = "".join(p[0] for p in user["nombre"].split()[:2])
                perfil = auth.profiles()[user["perfil"]]["nombre"]
                st.markdown(f'<div class="edu-user"><div class="av">{esc(initials)}</div><div>'
                            f'<div class="nm">{esc(user["nombre"])}</div><div class="rl">{esc(user["cargo"])}</div>'
                            f'<div class="rl">Perfil: {esc(perfil)}</div></div></div>', unsafe_allow_html=True)
                st.button("Cerrar sesión", on_click=logout, icon=":material/logout:", use_container_width=True)


user = st.session_state.get("user")
if not user:
    st.navigation([st.Page(login_page, title="Ingreso", icon=":material/login:")], position="hidden").run()
else:
    files = {"inicio": "inicio", "datos": "datos", "seguimiento": "seguimiento", "tecnologia": "tecnologia",
             "regiones": "regiones", "analisis": "analisis", "decisiones": "decisiones",
             "administracion": "administracion"}
    defs = {k: st.Page(f"views/{files[k]}.py", title=auth.PAGINAS[k], icon=ICONS[k], default=(k == "inicio"))
            for k in files}
    keys = [k for k in defs if k in user["paginas"]]
    nav = st.navigation([defs[k] for k in keys], position="hidden")
    masthead(user, keys, defs, nav)
    nav.run()
