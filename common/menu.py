"""Menú lateral común a todas las páginas."""
import streamlit as st

from common.login import generar_login, logout


def crear_menu() -> None:
    """Enlaces a las páginas, usuario activo y botón de salir."""
    with st.sidebar:
        st.title("Viajes y fatiga")
        st.page_link("home.py", label="Inicio", icon="🏠")
        st.page_link("pages/1_calendario_viajes.py", label="Calendario y viajes", icon="✈️")
        st.page_link("pages/2_fatiga_rotaciones.py", label="Fatiga y rotaciones", icon="🏀")
        st.divider()
        st.caption(f"Usuario: {st.session_state.get('usuario', '')}")
        if st.button("Salir"):
            logout()


def iniciar_pagina(titulo: str, icono: str) -> bool:
    """Configura la página, exige sesión y pinta el menú; devuelve False si hay que parar."""
    st.set_page_config(page_title=titulo, page_icon=icono, layout="wide")
    if not generar_login():
        return False
    crear_menu()
    return True
