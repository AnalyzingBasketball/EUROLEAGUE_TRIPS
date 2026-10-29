"""Informe PDF en memoria con fpdf2. Fuente DejaVu (viene con Matplotlib) para tildes, ñ, ≥ y ±."""
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
import pandas as pd
from fpdf import FPDF
from PIL import Image as PILImage

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
MAX_CELL_CHARS = 26


@dataclass
class Table:
    """Tabla del informe; solo se imprimen las primeras `max_rows` filas."""

    title: str
    df: pd.DataFrame
    max_rows: int = 30


@dataclass
class Image:
    """Gráfica PNG del informe."""

    title: str
    png: bytes
    note: str = ""


class _Report(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(110)
        self.cell(0, 8, f"Página {self.page_no()}", align="C")


def _fmt(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = f"{value:g}" if isinstance(value, float) else str(value)
    return text if len(text) <= MAX_CELL_CHARS else text[: MAX_CELL_CHARS - 1] + "…"


def build_report(title: str, user: str, filters: dict[str, str], blocks: list[Table | Image]) -> bytes:
    """Genera el PDF (horizontal, A4) y devuelve sus bytes."""
    pdf = _Report(orientation="L", unit="mm", format="A4")
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(90)
    pdf.cell(0, 6, f"Generado el {datetime.now().astimezone():%d/%m/%Y} por {user}", new_x="LMARGIN", new_y="NEXT")
    if filters:
        pdf.multi_cell(0, 5, " · ".join(f"{k}: {v}" for k, v in filters.items()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0)
    pdf.ln(3)

    for block in blocks:
        if isinstance(block, Image) and pdf.will_page_break(8 + _image_height(pdf, block) + 10):
            pdf.add_page()  # título y gráfica siempre en la misma página
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 8, block.title, new_x="LMARGIN", new_y="NEXT")
        if isinstance(block, Table):
            _add_table(pdf, block)
        else:
            _add_image(pdf, block)
        pdf.ln(3)
    return bytes(pdf.output())


def _add_table(pdf: FPDF, block: Table) -> None:
    pdf.set_font("DejaVu", "", 7)
    if block.df.empty:
        pdf.cell(0, 6, "Sin datos con estos filtros.", new_x="LMARGIN", new_y="NEXT")
        return
    shown = block.df.head(block.max_rows)
    with pdf.table(text_align="LEFT", line_height=4.5, padding=0.6) as table:
        header = table.row()
        for col in shown.columns:
            header.cell(str(col))
        for row in shown.itertuples(index=False):
            cells = table.row()
            for value in row:
                cells.cell(_fmt(value))
    if len(block.df) > len(shown):
        pdf.set_font("DejaVu", "", 8)
        pdf.cell(0, 6, f"Se muestran {len(shown)} de {len(block.df)} filas.", new_x="LMARGIN", new_y="NEXT")


def _image_width(pdf: FPDF) -> float:
    return min(190, pdf.epw)


def _image_height(pdf: FPDF, block: Image) -> float:
    """Alto en mm que ocupará la gráfica al escalarla al ancho de la página."""
    width_px, height_px = PILImage.open(BytesIO(block.png)).size
    return _image_width(pdf) * height_px / width_px


def _add_image(pdf: FPDF, block: Image) -> None:
    pdf.image(BytesIO(block.png), x=pdf.l_margin, w=_image_width(pdf))
    if block.note:
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(90)
        pdf.multi_cell(0, 4.5, block.note, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
