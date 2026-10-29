"""Tema claro u oscuro del navegador, para elegir la paleta de los gráficos."""
import streamlit as st


def is_dark() -> bool:
    """True si Streamlit está en tema oscuro; claro si no se puede saber."""
    try:
        return st.context.theme.type == "dark"
    except (AttributeError, RuntimeError):
        return False
