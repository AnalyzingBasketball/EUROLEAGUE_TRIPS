"""Descarga de la ACB: calendario y resultados (acb.com) y minutos por jugador (live.acb.com).

Solo existe la temporada en curso: la página del calendario no admite otra. Guarda en data/raw/acb/:
  calendario_<año>.json   partidos, resultados y estado (se descarga entero cada vez, es una sola petición)
  minutos_<año>.json      minutos de cada partido jugado, por id (solo se piden los que faltan)

Las dos webs permiten el acceso en su robots.txt. El script se identifica con un User-Agent propio y espera
entre peticiones. Uso: python scripts/fetch_acb.py [--pause 1.0]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _http import get

from controllers.acb_parse import parse_calendar, parse_match_stats

CALENDAR_URL = "https://acb.com/es/liga/calendario"
STATS_URL = "https://live.acb.com/es/partidos/{match_id}/estadisticas"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "acb"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=1.0, help="segundos entre peticiones")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    calendar = parse_calendar(get(CALENDAR_URL).text)
    year = calendar["temporada"]
    (OUT_DIR / f"calendario_{year}.json").write_text(json.dumps(calendar, ensure_ascii=False), encoding="utf-8")
    played = [m for m in calendar["partidos"] if m["jugado"]]
    print(f"ACB {year}: {len(calendar['partidos'])} partidos, {len(played)} jugados")

    path = OUT_DIR / f"minutos_{year}.json"
    minutes = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = [m for m in played if str(m["id"]) not in minutes]
    for n, match in enumerate(missing, 1):
        time.sleep(args.pause)
        html = get(STATS_URL.format(match_id=match["id"])).text
        minutes[str(match["id"])] = parse_match_stats(html, match["pts_local"], match["pts_visitante"])
        if n % 10 == 0 or n == len(missing):
            path.write_text(json.dumps(minutes, ensure_ascii=False), encoding="utf-8")
            print(f"minutos: {n}/{len(missing)}")
    print(f"{path.name}: {len(minutes)} partidos con minutos")


if __name__ == "__main__":
    main()
