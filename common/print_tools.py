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
button { font: 600 14px sans-serif; padding: 7px 12px; white-space: nowrap; width: 100%; border-radius: 8px; border: 1px solid #888;
         background: transparent; color: #0b0b0b; cursor: pointer; }
@media (prefers-color-scheme: dark) { button { color: #f0efec; } }
</style>
<button onclick="window.parent.print()">🖨️ Imprimir página</button>
"""


def print_button() -> None:
    """Pinta el botón de imprimir y añade los estilos que ocultan menú y botones en la vista de impresión."""
    st.markdown(PRINT_CSS, unsafe_allow_html=True)
    st.iframe(PRINT_BUTTON, height=46)
