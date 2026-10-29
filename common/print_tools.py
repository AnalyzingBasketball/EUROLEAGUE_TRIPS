"""Botón de imprimir la página y estilos de impresión."""
import streamlit as st

PRINT_CSS = """
<style>
@media print {
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
  [data-testid="stDownloadButton"], iframe, .no-print { display: none !important; }
  [data-testid="stMain"], .main { margin: 0 !important; overflow: visible !important; }
  .block-container { max-width: 100% !important; padding: 0.5rem !important; }
}
</style>
"""

PRINT_BUTTON = """
<style>
html, body { margin: 0; padding: 0; background: transparent; }
button { box-sizing: border-box; width: 100%; height: 40px; padding: 0 12px; border-radius: 8px;
         border: 1px solid rgba(128, 128, 128, 0.45); background: transparent; color: #0b0b0b; cursor: pointer;
         font: 400 16px "Source Sans", "Source Sans Pro", sans-serif; white-space: nowrap; }
button:hover { border-color: #ff4b4b; color: #ff4b4b; }
@media (prefers-color-scheme: dark) { button { color: #f0efec; } }
</style>
<button onclick="window.parent.print()">🖨️ Imprimir página</button>
"""


def inject_print_css() -> None:
    """Estilos de impresión: ocultan menú y botones. Se llama desde el menú para no añadir un hueco junto a los botones."""
    st.markdown(PRINT_CSS, unsafe_allow_html=True)


def print_button() -> None:
    """Botón que abre el diálogo de impresión del navegador."""
    st.iframe(PRINT_BUTTON, height=40)
