import pandas as pd
import pytest

from controllers.charts import (
    PALETTES,
    effect_figure,
    km_by_club_figure,
    trip_map_figure,
)


@pytest.mark.parametrize("dark", [False, True])
def test_km_figure_one_trace_per_competition(dark):
    data = pd.DataFrame({"Club": ["A", "A", "B"], "Competición": ["ACB", "E", "E"], "Km": [10.0, 20.0, 5.0]})
    fig = km_by_club_figure(data, dark)
    assert [t.name for t in fig.data] == ["ACB", "Euroliga"]
    assert fig.data[0].marker.color == PALETTES[dark]["ACB"]


def test_competition_colors_do_not_depend_on_which_competitions_are_shown():
    only_e = pd.DataFrame({"Club": ["A"], "Competición": ["E"], "Km": [1.0]})
    both = pd.DataFrame({"Club": ["A", "A"], "Competición": ["ACB", "E"], "Km": [1.0, 1.0]})
    assert km_by_club_figure(only_e, False).data[0].marker.color == km_by_club_figure(both, False).data[1].marker.color


def test_trip_map_draws_lines_and_markers():
    venues = pd.DataFrame({"nombre": ["A", "B"], "pais": ["es", "gr"], "lat": [40.0, 38.0], "lon": [-3.0, 23.0],
                           "partidos": [4, 1], "revisar": [0, 0]})
    lines = pd.DataFrame({"base_lat": [40.0], "base_lon": [-3.0], "destino_lat": [38.0], "destino_lon": [23.0]})
    assert len(trip_map_figure(venues, lines, False).data) == 2
    assert len(trip_map_figure(venues, None, False).data) == 1


def test_effect_figure_has_error_bars_and_order():
    data = pd.DataFrame({"tramo": ["a", "b", "a"], "competicion_id": ["ACB", "ACB", "E"], "media": [1.0, 2.0, 3.0],
                         "n": [5, 6, 7], "se": [0.5, 0.2, 0.1]})
    fig = effect_figure(data, "y", "x", True)
    assert list(fig.data[0].error_y.array) == pytest.approx([0.98, 0.392])
    assert fig.data[0].name == "ACB"
