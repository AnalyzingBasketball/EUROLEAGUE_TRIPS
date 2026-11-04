"""Escudos de los clubes: PNG de assets/escudos que las tablas muestran como imágenes incrustadas (data URI)."""
import base64
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "escudos.csv"
ASSETS = ROOT / "assets" / "escudos"
THUMB = 32  # lado máximo en píxeles: basta para una celda de tabla y mantiene ligero lo que se envía al navegador
CACHE_TTL = 24 * 3600  # el índice y los archivos son estáticos dentro de una publicación


def encode_data_uri(img: Image.Image) -> str:
    """Imagen PNG de paleta reducida como data URI, el formato que admiten las columnas de imagen de Streamlit."""
    quantized = img.convert("RGBA").quantize(colors=48, method=Image.Quantize.FASTOCTREE)  # PNG mucho más pequeño
    buffer = BytesIO()
    quantized.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def to_data_uri(path: Path, size: int = THUMB) -> str:
    """Miniatura de un escudo como data URI, con el lado mayor limitado a `size` píxeles."""
    with Image.open(path) as img:
        thumb = img.convert("RGBA")
        thumb.thumbnail((size, size), Image.LANCZOS)
        return encode_data_uri(thumb)


@st.cache_data(ttl=CACHE_TTL)
def get_crest_uris() -> dict[str, str]:
    """Nombre de club -> escudo como data URI (para las columnas de imagen de las tablas)."""
    index = pd.read_csv(CSV_PATH)
    return {row.club: to_data_uri(ASSETS / row.archivo) for row in index.itertuples()}
