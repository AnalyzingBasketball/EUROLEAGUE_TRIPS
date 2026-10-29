import numpy as np
import pandas as pd
import pytest

from controllers.chart_data import (
    binned_effect,
    default_season,
    km_by_club,
    mark_dual,
    trip_lines,
    venue_counts,
)

VENUES = pd.DataFrame({"id": [1, 2, 3], "nombre": ["A", "B", "C"], "pais": ["es", "es", "gr"],
                       "lat": [40.0, 41.0, 38.0], "lon": [-3.0, 2.0, 23.0], "revisar": [0, 0, 1]})


def _metrics(rows):
    return pd.DataFrame(rows, columns=["partido_id", "club_id", "competicion_id", "temporada_id", "home",
                                       "sede_id", "base_sede_id", "km_trip", "rest_days", "km_7d", "margin_resid"])


def test_default_season_skips_season_in_progress():
    rows = [(f"{s}-{i}", 1, "E", s) for s, n in ((2024, 10), (2025, 10), (2026, 2)) for i in range(n)]
    m = pd.DataFrame(rows, columns=["partido_id", "club_id", "competicion_id", "temporada_id"])
    assert default_season(m) == 2025


def test_mark_dual_flags_clubs_with_two_competitions():
    m = pd.DataFrame({"club_id": [1, 2], "temporada_id": [2025, 2025]})
    clubs = pd.DataFrame({"club_id": [1, 1, 2], "temporada_id": [2025] * 3, "competicion_id": ["ACB", "E", "E"]})
    assert list(mark_dual(m, clubs)["dual"]) == [True, False]


def test_km_by_club_sums_and_keeps_top_n():
    m = _metrics([("a", 1, "E", 2025, 0, 2, 1, 1000, 3, 0, 0), ("b", 1, "ACB", 2025, 0, 2, 1, 500, 3, 0, 0),
                  ("c", 2, "E", 2025, 0, 3, 1, 200, 3, 0, 0)])
    out = km_by_club(m, {1: "X", 2: "Y"}, top=1)
    assert set(out["Club"]) == {"X"}
    assert out["Km"].sum() == 1500


def test_venue_counts_counts_each_game_once():
    m = _metrics([("a", 1, "E", 2025, 1, 1, 1, 0, 3, 0, 0), ("a", 2, "E", 2025, 0, 1, 2, 10, 3, 0, 0),
                  ("b", 1, "E", 2025, 1, 1, 1, 0, 3, 0, 0)])
    out = venue_counts(m, VENUES)
    assert out.loc[out["nombre"] == "A", "partidos"].iloc[0] == 2


def test_trip_lines_only_away_games():
    m = _metrics([("a", 1, "E", 2025, 1, 1, 1, 0, 3, 0, 0), ("b", 1, "E", 2025, 0, 3, 1, 10, 3, 0, 0),
                  ("c", 1, "E", 2025, 0, 3, 1, 10, 3, 0, 0)])
    out = trip_lines(m, VENUES)
    assert len(out) == 1
    assert (out.loc[0, "base_nombre"], out.loc[0, "destino_nombre"], out.loc[0, "veces"]) == ("A", "C", 2)


def test_binned_effect_means_counts_and_se():
    m = _metrics([("a", 1, "E", 2025, 0, 1, 1, 0, 2, 0, 4.0), ("b", 1, "E", 2025, 0, 1, 1, 0, 2, 0, 6.0),
                  ("c", 1, "E", 2025, 0, 1, 1, 0, 6, 0, -2.0), ("d", 1, "E", 2025, 0, 1, 1, 0, np.nan, 0, 9.0)])
    out = binned_effect(m, "rest_days", "margin_resid").set_index("tramo")
    assert out.loc["2 días o menos", "media"] == 5.0
    assert out.loc["2 días o menos", "n"] == 2
    assert out.loc["2 días o menos", "se"] == pytest.approx(1.0)
    assert out.loc["6-7 días", "se"] == 0.0  # una sola observación: sin error estándar definido
    assert out["n"].sum() == 3  # la fila sin descanso se excluye


def test_binned_effect_zero_km_has_its_own_bin():
    m = _metrics([("a", 1, "E", 2025, 1, 1, 1, 0, 3, 0.0, 1.0), ("b", 1, "E", 2025, 0, 1, 1, 0, 3, 500.0, 1.0)])
    out = binned_effect(m, "km_7d", "margin_resid")
    assert set(out["tramo"].astype(str)) == {"Sin viaje (0 km)", "1-1.000 km"}
