import importlib.util
import json

import pytest

from controllers.acb_parse import minutes_to_float, parse_calendar, parse_match_stats

needs_bs4 = pytest.mark.skipif(importlib.util.find_spec("bs4") is None, reason="bs4 solo hace falta para la ingesta")


def _calendar_html(rounds: list, teams: list) -> str:
    """Página mínima con el formato de Next.js: equipos y jornadas dentro de un fragmento `__next_f.push`."""
    payload = f'{{"data":{{"teams":{json.dumps(teams)},"rounds":{json.dumps(rounds)}}}}}'
    return f'<script>self.__next_f.push([1,{json.dumps(payload)}])</script>'


def _match(match_id: int, home: int, away: int, status: str, pts=(0, 0)) -> dict:
    return {"id": match_id, "homeTeam": f"$4c:props:data:teams:{home}", "awayTeam": f"$4c:props:data:teams:{away}",
            "homeTeamScore": pts[0], "awayTeamScore": pts[1], "startDateTime": "2026-09-26T16:00:00Z",
            "matchStatus": status, "seasonStartYear": 2026}


TEAMS = [{"abbreviatedName": "BAR", "fullName": "Barça"}, {"abbreviatedName": "K&U", "fullName": "Kids&Us Manresa"}]


def test_calendar_reads_teams_scores_and_status():
    rounds = [{"roundNumber": 1, "matches": [_match(1, 0, 1, "FINALIZED", (90, 80)), _match(2, 1, 0, "NOT_STARTED")]}]
    cal = parse_calendar(_calendar_html(rounds, TEAMS))
    assert cal["temporada"] == 2026
    played, upcoming = cal["partidos"]
    assert (played["home"], played["away"], played["pts_local"], played["pts_visitante"]) == ("BAR", "K&U", 90, 80)
    assert played["jugado"] and played["fecha_utc"] == "2026-09-26T16:00:00"
    assert not upcoming["jugado"] and upcoming["pts_local"] is None  # el 0-0 de un partido sin jugar no es un resultado


def test_calendar_fails_when_page_changes():
    with pytest.raises(ValueError):
        parse_calendar("<html>sin datos</html>")


def test_minutes_to_float():
    assert minutes_to_float("21:02") == pytest.approx(21.033, abs=0.01)
    assert minutes_to_float("") == 0.0


def _table(rows: list[tuple[str, str, int, bool]], total: int) -> str:
    body = "".join(
        f'<tr><td><span class="playerName"><span>{i}</span> {name}</span>'
        f'{"<svg class=playerStarterIcon></svg>" if starter else ""}</td><td>{mins}</td><td>{pts}</td></tr>'
        for i, (name, mins, pts, starter) in enumerate(rows, 1)
    )
    return (f"<table><tr><th>Jugador</th><th>Min</th><th>Pts</th></tr>{body}"
            f"<tr><td>Totales</td><td></td><td>{total}</td></tr></table>")


STATS = ("<html>" + _table([("A. Uno", "30:00", 20, True), ("B. Dos", "", 0, False)], 20)
         + _table([("C. Tres", "10:30", 15, False)], 15) + "</html>")


@needs_bs4
def test_match_stats_skips_players_without_minutes_and_marks_starters():
    stats = parse_match_stats(STATS, 20, 15)
    assert stats["local"] == [{"jugador": "A. Uno", "titular": 1, "minutos": 30.0, "puntos": 20}]
    assert stats["visitante"] == [{"jugador": "C. Tres", "titular": 0, "minutos": 10.5, "puntos": 15}]


@needs_bs4
def test_match_stats_swaps_sides_when_the_score_says_so():
    stats = parse_match_stats(STATS, 15, 20)
    assert stats["local"][0]["jugador"] == "C. Tres"


@needs_bs4
def test_match_stats_rejects_totals_that_do_not_match():
    with pytest.raises(ValueError):
        parse_match_stats(STATS, 99, 15)
