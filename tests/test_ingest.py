import pytest

from controllers.ingest import (
    Venue,
    alias_ranges,
    club_canonical,
    group_venues,
    haversine_km,
    norm,
    parse_api_game,
    same_venue,
)


def _game(**over):
    base = {
        "gameCode": 7, "season": {"year": 2025}, "played": True,
        "date": "2025-10-02T20:00:00", "localDate": "2025-10-02T21:00:00", "utcDate": "2025-10-02T18:00:00Z",
        "round": 2, "phaseType": {"name": "Regular Season"},
        "local": {"club": {"code": "MAD", "name": "Real Madrid"}, "score": 90},
        "road": {"club": {"code": "BAR", "name": "FC Barcelona"}, "score": 80},
        "venue": {"code": "ATI"},
    }
    base.update(over)
    return base


def test_norm_strips_accents_and_case():
    assert norm("  Río  Breogán ") == "rio breogan"


def test_haversine_madrid_barcelona():
    assert haversine_km(40.4168, -3.7038, 41.3874, 2.1686) == pytest.approx(505, abs=5)


def test_haversine_zero():
    assert haversine_km(10, 10, 10, 10) == 0


def test_same_venue_by_name_even_if_far():
    a = Venue("a", "Sports Hall", 41.0, 29.0, "calle")
    b = Venue("b", "SPORTS  hall", 41.1, 29.1, "calle")
    assert same_venue(a, b)


def test_same_venue_by_distance_requires_precise_coordinates():
    a = Venue("a", "Hall A", 41.0, 29.0, "ciudad")
    b = Venue("b", "Hall B", 41.0, 29.0, "pabellon")
    assert not same_venue(a, b)
    assert same_venue(Venue("a", "Hall A", 41.0, 29.0, "calle"), b)


def test_group_venues_merges_transitively():
    vs = [Venue("1", "X", 0, 0, "calle"), Venue("2", "x", 50, 50, "calle"), Venue("3", "Y", 10, 10, "calle")]
    g = group_venues(vs)
    assert g["1"] == g["2"] != g["3"]


def test_parse_api_game_played():
    r = parse_api_game(_game(), "E")
    assert r["fecha"] == "2025-10-02"
    assert r["hora_utc"] == "2025-10-02T18:00:00"
    assert (r["pts_local"], r["pts_visitante"], r["jugado"]) == (90, 80, 1)
    assert r["venue_code"] == "ATI"


def test_parse_api_game_unplayed_has_no_score():
    r = parse_api_game(_game(played=False), "E")
    assert r["pts_local"] is None and r["pts_visitante"] is None and r["jugado"] == 0


def test_parse_api_game_skips_virtual_club():
    g = _game()
    g["road"]["club"]["isVirtual"] = True
    assert parse_api_game(g, "E") is None


def test_parse_api_game_without_venue():
    assert parse_api_game(_game(venue=None), "E")["venue_code"] is None


def test_club_canonical_prefers_crosswalk_then_latest_name():
    names = {2022: "Cazoo Baskonia", 2025: "Kosner Baskonia"}
    assert club_canonical("E", "BAS", names, {("E", "BAS"): "Baskonia"}) == "Baskonia"
    assert club_canonical("E", "BAS", names, {}) == "Kosner Baskonia"


def test_alias_ranges_open_ended_when_current():
    rows = [("E", "BAS", "Cazoo", 2022), ("E", "BAS", "Kosner", 2025), ("E", "BAS", "Kosner", 2026),
            ("E", "BAS", "Cazoo", 2022)]
    assert alias_ranges(rows, 2026) == [("E", "BAS", "Cazoo", 2022, 2022), ("E", "BAS", "Kosner", 2025, None)]
