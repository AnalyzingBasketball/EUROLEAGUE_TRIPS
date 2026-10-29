"""Login con estado de sesión de Streamlit."""
import streamlit as st

from controllers.auth import validate_credentials


def logout() -> None:
    """Borra la sesión y recarga la página."""
    st.session_state.clear()
    st.rerun()


def generar_login() -> bool:
    """Pinta el formulario si no hay sesión; devuelve True cuando hay usuario autenticado."""
    if "usuario" in st.session_state:
        return True
    st.title("Viajes y fatiga en baloncesto europeo")
    st.caption("Inicia sesión para ver la aplicación.")
    with st.form("login"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        if validate_credentials(user, password):
            st.session_state["usuario"] = user
            st.rerun()
        st.error("Usuario o contraseña incorrectos.")
    return False
