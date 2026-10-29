"""Contornos de países (Natural Earth 110m, dominio público) para el mapa base del PDF."""
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "paises.json"


@lru_cache(maxsize=1)
def load_country_rings() -> list[list[list[float]]]:
    """Contornos exteriores recortados a Europa y Oriente Medio: lista de anillos [[lon, lat], ...]."""
    return json.loads(PATH.read_text(encoding="utf-8"))
