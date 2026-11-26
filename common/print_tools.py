"""Botón de imprimir la página y estilos de impresión."""
import pandas as pd
import streamlit as st

from common.utils import inject_css

IMAGE_COLUMNS = ("Escudo", "Escudo rival", "Escudo visitante", "Bandera")

PRINT_BUTTON = """
<style>
html, body { margin: 0; padding: 0; background: transparent; }
button { box-sizing: border-box; width: 100%; height: 40px; padding: 0 12px; border-radius: 8px;
         border: 1px solid #ff4b4b; background: #ff4b4b; color: #ffffff; cursor: pointer;
         font: 400 14px "Source Sans", "Source Sans Pro", sans-serif; white-space: nowrap; }
button:hover { border-color: #ff6b6b; background: #ff6b6b; }
</style>
<button onclick="imprimir()">🖨️ Imprimir página</button>
<script>
// Los gráficos de Plotly tienen un ancho fijo en píxeles: se reducen para que quepan en la hoja y se restauran después.
function imprimir() {
  const padre = window.parent;
  const MAX = 1000;
  padre.document.querySelectorAll('[data-testid="stPlotlyChart"]').forEach((el) => {
    const ancho = el.getBoundingClientRect().width;
    if (ancho > MAX) { el.style.zoom = String(MAX / ancho); el.dataset.ajustado = "1"; }
  });
  padre.addEventListener("afterprint", () => {
    padre.document.querySelectorAll('[data-ajustado]').forEach((el) => { el.style.zoom = ""; delete el.dataset.ajustado; });
  }, { once: true });
  padre.print();
}
</script>
"""


def inject_print_css() -> None:
    """Estilos de impresión (styles/print.css): ocultan menú y botones. Se llama desde el menú para no añadir un hueco junto a los botones."""
    inject_css("print.css")


def print_button() -> None:
    """Botón que abre el diálogo de impresión del navegador."""
    st.iframe(PRINT_BUTTON, height=40)


def print_table(table: pd.DataFrame, rows: int = 40) -> None:
    """Copia estática de una tabla, visible solo al imprimir: la tabla interactiva se dibuja en un lienzo y sale recortada."""
    shown = table.drop(columns=[c for c in IMAGE_COLUMNS if c in table.columns]).head(rows)
    # Los números enteros guardados como decimales (4466.0) se muestran sin decimales.
    formats = {c: (lambda v: "" if pd.isna(v) else str(int(v)) if v == int(v) else str(round(v, 4)))
               for c in shown.select_dtypes("number").columns}
    note = f"<p>Se imprimen las {len(shown)} primeras filas de {len(table)}.</p>" if len(table) > rows else ""
    st.html(f'<div class="print-only">{shown.to_html(index=False, border=0, na_rep="", formatters=formats)}{note}</div>')
