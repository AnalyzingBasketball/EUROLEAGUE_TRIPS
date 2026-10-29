import pandas as pd
import pytest

from controllers.metrics import build_metrics
from controllers.views import (
    club_names,
    fatigue_table,
    filter_metrics,
    seasons_label,
    trip_table,
    upcoming_games,
)

SEDES = pd.DataFrame({"id": [10, 20], "nombre": ["Madrid", "Barcelona"], "lat": [40.4, 41.4], "lon": [-3.7, 2.1]})
GAMES = pd.DataFrame([
    ("g1", "ACB", 2025, "2025-10-01", None, 1, 2, 10, 1, 90, 80),
    ("g2", "E", 2025, "2025-10-05", None, 2, 1, 20, 1, 70, 75),
    ("g3", "ACB", 2024, "2024-10-05", None, 2, 1, 20, 1, 70, 75),
], columns=["id", "competicion_id", "temporada_id", "fecha", "hora_utc", "local_id", "visitante_id",
            "sede_id", "jugado", "pts_local", "pts_visitante"])
MINUTES = pd.DataFrame(columns=["partido_id", "club_id", "jugador", "titular", "minutos"])
NAMES = {1: "Real Madrid", 2: "Barça"}


@pytest.fixture()
def metrics():
    return build_metrics(GAMES, SEDES, MINUTES)


def test_seasons_label():
    assert seasons_label(2025) == "2025/26"


def test_club_names():
    clubs = pd.DataFrame({"club_id": [1, 2], "club": ["A", "B"]})
    assert club_names(clubs) == {1: "A", 2: "B"}


def test_filter_by_season_competition_and_club(metrics):
    assert len(filter_metrics(metrics, 2025, ["ACB", "E"])) == 4
    assert len(filter_metrics(metrics, 2025, ["E"])) == 2
    assert set(filter_metrics(metrics, 2025, ["ACB", "E"], club_id=1)["club_id"]) == {1}


def test_trip_table_columns_and_result(metrics):
    t = trip_table(filter_metrics(metrics, 2025, ["ACB"], 1), NAMES, SEDES)
    assert t.loc[0, "Resultado"] == "90-80"
    assert t.loc[0, "Condición"] == "Local"
    assert t.loc[0, "Sede"] == "Madrid"
    assert "Km 7 días" in t.columns


def test_fatigue_table_handles_missing_minutes(metrics):
    t = fatigue_table(filter_metrics(metrics, 2025, ["ACB", "E"]), NAMES)
    assert t["Jugadores ≥10 min"].isna().all()
    assert len(t) == 4


def test_upcoming_games_only_unplayed_sorted_and_limited():
    live = pd.DataFrame({
        "fecha": ["2026-11-02", "2026-11-01", "2026-10-01"], "hora_utc": ["2026-11-02T19:00:00", None, None],
        "jornada": [5, 5, 1], "local_name": ["A", "B", "C"], "road_name": ["D", "E", "F"], "jugado": [0, 0, 1],
    })
    t = upcoming_games(live, limit=1)
    assert list(t["Local"]) == ["B"]
    assert len(upcoming_games(live)) == 2
