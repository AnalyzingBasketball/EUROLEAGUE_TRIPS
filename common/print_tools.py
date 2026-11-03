"""Botón de imprimir la página y estilos de impresión."""
import streamlit as st

from common.utils import inject_css

PRINT_BUTTON = """
<style>
html, body { margin: 0; padding: 0; background: transparent; }
button { box-sizing: border-box; width: 100%; height: 40px; padding: 0 12px; border-radius: 8px;
         border: 1px solid #ff4b4b; background: #ff4b4b; color: #ffffff; cursor: pointer;
         font: 400 14px "Source Sans", "Source Sans Pro", sans-serif; white-space: nowrap; }
button:hover { border-color: #ff6b6b; background: #ff6b6b; }
</style>
<button onclick="window.parent.print()">🖨️ Imprimir página</button>
"""


def inject_print_css() -> None:
    """Estilos de impresión (styles/print.css): ocultan menú y botones. Se llama desde el menú para no añadir un hueco junto a los botones."""
    inject_css("print.css")


def print_button() -> None:
    """Botón que abre el diálogo de impresión del navegador."""
    st.iframe(PRINT_BUTTON, height=40)
