"""Utilidades compartidas: carga de hojas de estilo de la carpeta styles/."""
from functools import cache
from pathlib import Path

import streamlit as st

STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"


@cache
def load_css(name: str) -> str:
    """Contenido de un archivo de styles/ (por ejemplo, «print.css»)."""
    return (STYLES_DIR / name).read_text(encoding="utf-8")


def inject_css(name: str) -> None:
    """Aplica a la página una hoja de estilo de styles/."""
    st.markdown(f"<style>{load_css(name)}</style>", unsafe_allow_html=True)
