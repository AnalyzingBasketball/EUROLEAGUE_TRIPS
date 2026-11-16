"""Petición HTTP común a los scripts de descarga: se identifica con claridad, espera entre peticiones y reintenta."""
import time

import requests

USER_AGENT = "MPAD-M8-tarea-academica (proyecto del Master en Python Avanzado Aplicado al Deporte)"
MAX_RETRIES = 5


def get(url: str, params: dict | None = None) -> requests.Response:
    """GET con reintentos: espera más cada vez ante 429 o error del servidor y falla si se agotan."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
        except requests.RequestException:
            time.sleep(5 * attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(5 * attempt)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"No se pudo descargar {url} tras {MAX_RETRIES} intentos")
