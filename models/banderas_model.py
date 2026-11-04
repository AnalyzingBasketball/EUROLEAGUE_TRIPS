"""Banderas de los países de las sedes: PNG de assets/banderas (nombre = código ISO de dos letras) como data URI."""
from pathlib import Path

import streamlit as st

from models.escudos_model import CACHE_TTL, to_data_uri

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "banderas"
THUMB = 40  # las banderas son apaisadas: a 40 px de ancho miden unos 27 de alto, legibles en una celda


@st.cache_data(ttl=CACHE_TTL)
def get_flag_uris() -> dict[str, str]:
    """Código de país (`es`, `fr`...) -> bandera como data URI, para las columnas de imagen de las tablas."""
    return {path.stem: to_data_uri(path, THUMB) for path in sorted(ASSETS.glob("*.png"))}
