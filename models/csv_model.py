"""Fuente 2: catálogo de sedes en CSV (geocodificado con OpenStreetMap, ODbL)."""
from pathlib import Path

import pandas as pd
import streamlit as st

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "sedes.csv"
CACHE_TTL = 24 * 3600  # el CSV es estático dentro de una publicación


@st.cache_data(ttl=CACHE_TTL)
def get_venues_csv() -> pd.DataFrame:
    """Sedes: nombre, país, coordenadas y precisión de la coordenada."""
    return pd.read_csv(CSV_PATH)
