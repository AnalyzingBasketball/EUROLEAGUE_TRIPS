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
<button onclick="imprimir()">Imprimir página</button>
<script>
// Los gráficos de Plotly tienen un ancho fijo en píxeles: se reducen para que quepan en la hoja y se restauran después.
function imprimir() {
  const padre = window.parent;
  const MAX = 680;  // ancho útil de un A4 vertical; Safari ignora @page y suele imprimir en vertical
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


def print_table(table: pd.DataFrame, rows: int = 40, chunk: int = 8) -> None:
    """Copia estática de una tabla, visible solo al imprimir: la tabla interactiva se dibuja en un lienzo y sale recortada.

    Se parte en bloques de `chunk` filas con la cabecera repetida: WebKit (Safari) no evita que una fila se corte entre
    páginas, pero sí que se corte un bloque. Las columnas tienen el mismo ancho en todos los bloques.
    """
    shown = table.drop(columns=[c for c in IMAGE_COLUMNS if c in table.columns]).head(rows)
    # Los números enteros guardados como decimales (4466.0) se muestran sin decimales.
    formats = {c: (lambda v: "" if pd.isna(v) else str(int(v)) if v == int(v) else str(round(v, 4)))
               for c in shown.select_dtypes("number").columns}
    weights = [max(len(str(c)) * 0.6, min(shown[c].astype(str).str.len().max(), 22)) if len(shown) else 1 for c in shown.columns]
    cols = "".join(f'<col style="width:{100 * w / sum(weights):.1f}%">' for w in weights)
    parts = []
    for start in range(0, len(shown), chunk):
        html = shown.iloc[start:start + chunk].to_html(index=False, border=0, na_rep="", formatters=formats)
        parts.append(f'<div class="print-chunk">{html.replace("<thead>", f"<colgroup>{cols}</colgroup><thead>", 1)}</div>')
    note = f"<p>Se imprimen las {len(shown)} primeras filas de {len(table)}.</p>" if len(table) > rows else ""
    st.html(f'<div class="print-only">{"".join(parts)}{note}</div>')
