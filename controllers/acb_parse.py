"""Lectura de las páginas públicas de la ACB: calendario (acb.com) y estadísticas de partido (live.acb.com).

Lógica pura sobre el HTML descargado; la descarga está en `scripts/fetch_acb.py`. `bs4` solo se importa al leer
estadísticas, porque la app publicada no lo necesita.
"""
import json
import re

PLAYED_STATUS = "FINALIZED"
_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.DOTALL)
_TEAM_REF = re.compile(r":teams:(\d+)$")


def _next_payload(html: str) -> str:
    """Une los fragmentos `self.__next_f.push` de Next.js en un solo texto."""
    chunks = _CHUNK.findall(html)
    if not chunks:
        raise ValueError("La página no trae datos de Next.js: ha cambiado el formato.")
    return "".join(json.loads(f'"{c}"') for c in chunks)


def parse_calendar(html: str) -> dict:
    """Calendario de la temporada en curso: equipos y partidos con resultado y estado.

    Cada partido lleva `home` y `away` como código ACB de tres letras (p. ej. «BAR», «K&U»).
    """
    payload = _next_payload(html)
    start = payload.find('"rounds":[')
    team_start = payload.rfind('"teams":[', 0, start)
    if start < 0 or team_start < 0:
        raise ValueError("No se encuentran las jornadas ni los equipos en la página.")
    decoder = json.JSONDecoder()
    rounds, _ = decoder.raw_decode(payload[start + len('"rounds":'):])
    teams, _ = decoder.raw_decode(payload[team_start + len('"teams":'):])
    matches = []
    for rnd in rounds:
        for m in rnd["matches"]:
            home = teams[int(_TEAM_REF.search(m["homeTeam"]).group(1))]
            away = teams[int(_TEAM_REF.search(m["awayTeam"]).group(1))]
            played = m["matchStatus"] == PLAYED_STATUS
            matches.append({
                "id": m["id"],
                "jornada": rnd["roundNumber"],
                "fecha_utc": m["startDateTime"].rstrip("Z"),
                "estado": m["matchStatus"],
                "jugado": played,
                "home": home["abbreviatedName"],
                "home_name": home["fullName"],
                "away": away["abbreviatedName"],
                "away_name": away["fullName"],
                "pts_local": m["homeTeamScore"] if played else None,
                "pts_visitante": m["awayTeamScore"] if played else None,
            })
    seasons = {m["seasonStartYear"] for rnd in rounds for m in rnd["matches"]}
    if len(seasons) != 1:
        raise ValueError(f"Se esperaba una sola temporada y hay {sorted(seasons)}.")
    return {"temporada": seasons.pop(), "partidos": matches}


def minutes_to_float(text: str) -> float:
    """«21:02» -> 21,03 minutos; vacío o ilegible -> 0."""
    match = re.fullmatch(r"\s*(\d+):(\d{2})\s*", text or "")
    return int(match.group(1)) + int(match.group(2)) / 60 if match else 0.0


def _team_rows(table) -> tuple[list[dict], int]:
    """Jugadores con minutos de una tabla de estadísticas y los puntos que suma la fila «Totales»."""
    rows, total = [], 0
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        if cells[0].get_text(" ", strip=True) == "Totales":
            total = int(cells[2].get_text(strip=True) or 0)
            continue
        name_tag = cells[0].select_one('[class*="playerName"]')
        if name_tag is None:
            continue
        dorsal = name_tag.find("span")
        if dorsal is not None:
            dorsal.extract()  # el dorsal va dentro del mismo texto que el nombre
        minutes = minutes_to_float(cells[1].get_text(strip=True))
        if minutes <= 0:
            continue  # no jugó
        rows.append({
            "jugador": name_tag.get_text(" ", strip=True),
            "titular": int(cells[0].select_one('[class*="playerStarterIcon"]') is not None),
            "minutos": round(minutes, 2),
            "puntos": int(cells[2].get_text(strip=True) or 0),
        })
    return rows, total


def parse_match_stats(html: str, pts_local: int, pts_visitante: int) -> dict:
    """Minutos, puntos y titulares de un partido: {«local»: [...], «visitante»: [...]}.

    La página trae dos tablas de jugadores (local y visitante) y repite una en una vista alternativa. Se comprueba
    con el marcador cuál es cuál y se falla si los puntos de la fila «Totales» no cuadran, para no guardar un
    partido mal leído.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    tables = [t for t in soup.find_all("table") if any(th.get_text(strip=True) == "Jugador" for th in t.find_all("th"))]
    if len(tables) < 2:
        raise ValueError("Faltan las tablas de jugadores del partido.")
    first, second = _team_rows(tables[0]), _team_rows(tables[1])
    if (first[1], second[1]) == (pts_local, pts_visitante):
        local, away = first[0], second[0]
    elif (second[1], first[1]) == (pts_local, pts_visitante):
        local, away = second[0], first[0]
    else:
        raise ValueError(f"Los totales {first[1]}-{second[1]} no cuadran con el marcador {pts_local}-{pts_visitante}.")
    return {"local": local, "visitante": away}
