import pandas as pd

from controllers.map_charts import animated_map_figure, detail_map_figure
from controllers.map_data import (
    month_frames,
    month_label,
    route_lines,
    venue_games,
    venue_options,
    venue_stats,
)

NAMES = {1: "Club A", 2: "Club B", 3: "Club C"}
VENUES = pd.DataFrame({
    "id": [10, 20], "nombre": ["Pabellón A", "Pabellón B"], "ciudad": ["Madrid", "Atenas"], "pais": ["es", "gr"],
    "lat": [40.4, 38.0], "lon": [-3.7, 23.8],
})


def _metrics() -> pd.DataFrame:
    """Dos partidos, cada uno con las dos filas de club: A recibe a B (ACB) y C recibe a A (Euroliga)."""
    rows = [
        (100, "ACB", "2025-10-05", 1, 2, 1, 10, 10, 80, 70),
        (100, "ACB", "2025-10-05", 2, 1, 0, 10, 20, 70, 80),
        (200, "E", "2025-11-10", 3, 1, 1, 20, 20, 90, 85),
        (200, "E", "2025-11-10", 1, 3, 0, 20, 10, 85, 90),
    ]
    cols = ["partido_id", "competicion_id", "fecha", "club_id", "rival_id", "home", "sede_id", "base_sede_id",
            "pts_for", "pts_against"]
    out = pd.DataFrame(rows, columns=cols)
    out["fecha"] = pd.to_datetime(out["fecha"])
    return out


def test_venue_stats_counts_games_per_venue_and_competition():
    stats = venue_stats(_metrics(), VENUES, NAMES)
    row = stats[(stats["sede_id"] == 10) & (stats["competicion_id"] == "ACB")].iloc[0]
    assert row["partidos"] == 1 and row["total"] == 1 and row["clubes"] == "Club A"
    assert set(stats["sede_id"]) == {10, 20}


def test_route_lines_only_away_trips_with_round_trip_km():
    routes = route_lines(_metrics(), VENUES)
    assert len(routes) == 2  # B viaja de la sede 20 a la 10 y A de la 10 a la 20
    assert (routes["km"] > 4000).all()
    assert route_lines(_metrics(), VENUES, top=1).shape[0] == 1


def test_route_lines_without_away_games_is_empty():
    home_only = _metrics()[lambda d: d["home"] == 1]
    assert route_lines(home_only, VENUES).empty


def test_month_frames_are_cumulative_and_labelled_in_spanish():
    frames = month_frames(_metrics(), VENUES, NAMES, with_routes=True)
    assert [f[0] for f in frames] == ["octubre 2025", "noviembre 2025"]
    assert frames[0][1]["partidos"].sum() == 1 and frames[1][1]["partidos"].sum() == 2
    assert month_label(pd.Period("2026-01")) == "enero 2026"
    assert month_frames(_metrics(), VENUES, NAMES, with_routes=False)[1][2].empty


def test_venue_options_ranks_venues_by_games_with_a_readable_label():
    options = venue_options(venue_stats(_metrics(), VENUES, NAMES))
    assert list(options) == [10, 20] or list(options) == [20, 10]
    assert options[10] == "Pabellón A (Madrid) · 1 partidos"


def test_venue_games_shows_local_first_even_from_the_visitor_row():
    only_visitor = _metrics()[lambda d: (d["club_id"] == 2) & (d["sede_id"] == 10)]  # fila de B, que jugó fuera
    games = venue_games(only_visitor, 10, NAMES, {"Club A": "data:a", "Club B": "data:b"})
    assert list(games.columns) == ["Fecha", "Competición", "Escudo", "Local", "Escudo visitante", "Visitante", "Resultado"]
    assert games.loc[0, "Local"] == "Club A" and games.loc[0, "Visitante"] == "Club B"
    assert games.loc[0, "Resultado"] == "80-70"  # resultado desde el punto de vista del local


def test_detail_map_has_one_trace_per_route_plus_venues():
    stats = venue_stats(_metrics(), VENUES, NAMES)
    fig = detail_map_figure(stats, route_lines(_metrics(), VENUES), dark=False)
    assert len(fig.data) == 2 + 1 + 2  # dos rutas, puntos medios y una traza por competición con sedes
    assert fig.layout.map.style == "carto-positron"
    assert detail_map_figure(stats, route_lines(_metrics(), VENUES), dark=True).layout.map.style == "carto-darkmatter"


def test_animated_map_has_fixed_traces_and_one_frame_per_month():
    fig = animated_map_figure(month_frames(_metrics(), VENUES, NAMES, with_routes=True), dark=False)
    assert len(fig.data) == 6 and len(fig.frames) == 2
    assert [step["label"] for step in fig.layout.sliders[0].steps] == ["oct 2025", "nov 2025"]


def test_detail_map_highlights_the_chosen_venue_with_an_extra_trace():
    stats = venue_stats(_metrics(), VENUES, NAMES)
    plain = detail_map_figure(stats, route_lines(_metrics(), VENUES), dark=False)
    marked = detail_map_figure(stats, route_lines(_metrics(), VENUES), dark=False, highlight=10)
    assert len(marked.data) == len(plain.data) + 1
