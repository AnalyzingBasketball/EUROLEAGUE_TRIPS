"""Banderas de los países de las sedes: PNG de assets/banderas (nombre = código ISO de dos letras) como data URI."""
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw

from models.escudos_model import CACHE_TTL, encode_data_uri

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "banderas"
BOX = (40, 27)  # todas las banderas salen con el mismo tamaño y proporción 3:2, legibles en una celda
BORDER = (150, 150, 150, 255)  # marco fino: sin él, las franjas blancas (Polonia, Mónaco) se pierden en el fondo


def fit_to_box(img: Image.Image, box: tuple[int, int] = BOX) -> Image.Image:
    """Lleva la bandera a un tamaño fijo: las más altas se recortan arriba y abajo, las más anchas se aplanan."""
    width, height = box
    img = img.convert("RGBA")
    scaled_height = round(img.height * width / img.width)  # alto al ajustar el ancho de la caja
    img = img.resize((width, scaled_height), Image.LANCZOS)
    if scaled_height > height:  # más alta que 3:2 (Bélgica, Andorra): se recorta de forma centrada
        top = (scaled_height - height) // 2
        return img.crop((0, top, width, top + height))
    return img.resize((width, height), Image.LANCZOS)  # más ancha (Reino Unido, Emiratos): se estira en vertical


def flag_uri(path: Path) -> str:
    """Bandera como data URI de tamaño uniforme y con marco."""
    with Image.open(path) as img:
        flag = fit_to_box(img)
    ImageDraw.Draw(flag).rectangle((0, 0, flag.width - 1, flag.height - 1), outline=BORDER)
    return encode_data_uri(flag)


@st.cache_data(ttl=CACHE_TTL)
def get_flag_uris() -> dict[str, str]:
    """Código de país (`es`, `fr`...) -> bandera como data URI, para las columnas de imagen de las tablas."""
    return {path.stem: flag_uri(path) for path in sorted(ASSETS.glob("*.png"))}
