"""Fuente 1: base SQLite con partidos, sedes y minutos. Consultas con caché."""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from controllers.chart_data import mark_dual
from controllers.metrics import build_metrics
from models.db import connect
from models.partidos_model import load_clubs, load_games, load_minutes, load_venues

APP_DIR = Path(__file__).resolve().parent.parent
load_dotenv(APP_DIR / ".env")

# La base solo cambia al volver a publicar la app: un día de caché evita recalcular métricas en cada sesión.
CACHE_TTL = 24 * 3600


def _db_path() -> Path:
    return APP_DIR / os.getenv("DB_PATH", "data/viajes_fatiga.db")


@st.cache_resource
def get_connection():
    """Conexión de solo lectura compartida entre sesiones."""
    return connect(_db_path(), read_only=True)


@st.cache_data(ttl=CACHE_TTL)
def get_clubs() -> pd.DataFrame:
    """Clubes y competiciones por temporada."""
    return load_clubs(get_connection())


@st.cache_data(ttl=CACHE_TTL)
def get_venues() -> pd.DataFrame:
    """Sedes con coordenadas."""
    return load_venues(get_connection())


@st.cache_data(ttl=CACHE_TTL)
def get_metrics() -> pd.DataFrame:
    """Métricas de viaje, descanso, rotación y margen ajustado por club y partido jugado, con marca de doble competición."""
    conn = get_connection()
    metrics = build_metrics(load_games(conn), load_venues(conn), load_minutes(conn))
    return mark_dual(metrics, load_clubs(conn))
