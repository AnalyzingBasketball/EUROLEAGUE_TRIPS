"""Fuente 1: base SQLite con partidos, sedes y minutos. Consultas con caché."""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from controllers.chart_data import mark_dual
from controllers.metrics import build_metrics
from models.db import connect
from models.partidos_model import (
    load_aliases,
    load_clubs,
    load_games,
    load_minutes,
    load_venues,
)

APP_DIR = Path(__file__).resolve().parent.parent
load_dotenv(APP_DIR / ".env")

# La base solo cambia al volver a publicar la app: un día de caché evita recalcular métricas en cada sesión.
CACHE_TTL = 24 * 3600
METRICS_FILE = APP_DIR / "data" / "metricas.parquet"


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
def get_aliases() -> pd.DataFrame:
    """Códigos de club por competición y temporada (para reconocer los clubes que devuelve la API)."""
    return load_aliases(get_connection())


@st.cache_data(ttl=CACHE_TTL)
def get_venues() -> pd.DataFrame:
    """Sedes con coordenadas."""
    return load_venues(get_connection())


def compute_metrics(conn) -> pd.DataFrame:
    """Calcula las métricas de viaje, descanso, rotación y margen ajustado desde la base (tarda más de un segundo)."""
    metrics = build_metrics(load_games(conn), load_venues(conn), load_minutes(conn))
    return mark_dual(metrics, load_clubs(conn))


@st.cache_data(ttl=CACHE_TTL)
def get_metrics() -> pd.DataFrame:
    """Métricas por club y partido jugado, con marca de doble competición.

    Se leen ya calculadas de `data/metricas.parquet` (lo genera `scripts/precompute_metrics.py` tras construir la base):
    así la primera visita no gasta CPU en la regresión y la app arranca antes. Si el archivo falta, o se usa otra base
    con `DB_PATH`, se calculan al momento.
    """
    if METRICS_FILE.exists() and _db_path() == APP_DIR / "data" / "viajes_fatiga.db":
        return pd.read_parquet(METRICS_FILE)
    return compute_metrics(get_connection())
