"""Fuente 3: API pública de Euroliga/EuroCup (calendario en vivo)."""
import pandas as pd
import requests
import streamlit as st

from controllers.ingest import parse_api_game

BASE_URL = "https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{comp}{year}/games"
CACHE_TTL = 3600  # el calendario cambia a diario como mucho; una hora respeta el límite de peticiones


@st.cache_data(ttl=CACHE_TTL, show_spinner="Consultando la API de Euroliga...")
def get_live_games(comp: str, year: int) -> pd.DataFrame:
    """Partidos de una competición y temporada; lanza excepción si la API no responde."""
    resp = requests.get(BASE_URL.format(comp=comp, year=year), params={"limit": 1000}, timeout=20)
    resp.raise_for_status()
    rows = [parse_api_game(g, comp) for g in resp.json()["data"]]
    return pd.DataFrame([r for r in rows if r])
