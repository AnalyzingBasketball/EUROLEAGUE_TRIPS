"""Descarga de Euroliga (E) y EuroCup (U) desde la API pública v2 a data/raw/api/.

Por cada competición y temporada guarda:
  <comp><año>.json          calendario y resultados (se vuelve a pedir con --force)
  minutos_<comp><año>.json  minutos, puntos y titulares de cada partido jugado (solo se piden los que faltan)

Peticiones en serie con pausa y reintentos ante 429. Uso:
  python scripts/fetch_euroleague.py [--force] [--from 2026] [--to 2026] [--pause 1.0]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _http import get

SEASON_URL = "https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{comp}{year}/games"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "api"


def season_games(comp: str, year: int, path: Path, force: bool, pause: float) -> list[dict]:
    """Partidos de la temporada: del fichero si existe, de la API si falta o con --force."""
    if force or not path.exists():
        path.write_bytes(get(SEASON_URL.format(comp=comp, year=year), params={"limit": 1000}).content)
        print(f"{path.name}: descargado")
        time.sleep(pause)
    return json.loads(path.read_text(encoding="utf-8"))["data"]


def team_rows(side: dict) -> list[dict]:
    """Jugadores con minutos de un equipo: nombre, titular, minutos y puntos."""
    return [
        {"jugador": p["player"]["person"]["name"], "titular": int(bool(p["stats"].get("startFive"))),
         "minutos": round(p["stats"]["timePlayed"] / 60, 2), "puntos": int(p["stats"]["points"])}
        for p in side["players"] if p["stats"]["timePlayed"] > 0
    ]


def fetch_minutes(comp: str, year: int, games: list[dict], pause: float) -> None:
    """Pide /games/<n>/stats de los partidos jugados que aún no están en minutos_<comp><año>.json."""
    path = OUT_DIR / f"minutos_{comp}{year}.json"
    minutes = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = [g["gameCode"] for g in games if g.get("played") and str(g["gameCode"]) not in minutes]
    for n, code in enumerate(missing, 1):
        stats = get(f"{SEASON_URL.format(comp=comp, year=year)}/{code}/stats").json()
        minutes[str(code)] = {"local": team_rows(stats["local"]), "visitante": team_rows(stats["road"])}
        time.sleep(pause)
        if n % 25 == 0 or n == len(missing):
            path.write_text(json.dumps(minutes, ensure_ascii=False), encoding="utf-8")
            print(f"{path.name}: {n}/{len(missing)}")
    print(f"{path.name}: {len(minutes)} partidos con minutos")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="vuelve a pedir el calendario de cada temporada")
    parser.add_argument("--from", dest="first", type=int, default=2026)
    parser.add_argument("--to", dest="last", type=int, default=2026)
    parser.add_argument("--pause", type=float, default=1.0, help="segundos entre peticiones")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for comp in ("E", "U"):
        for year in range(args.first, args.last + 1):
            games = season_games(comp, year, OUT_DIR / f"{comp}{year}.json", args.force, args.pause)
            fetch_minutes(comp, year, games, args.pause)


if __name__ == "__main__":
    main()
