import pandas as pd
import pytest

from controllers.metrics import (
    add_adjusted_margin,
    add_rest_and_travel,
    add_rotation,
    build_club_games,
    build_metrics,
)

# Madrid (1), Barcelona (2) y Atenas (3). Distancias aproximadas: MAD-BCN 505 km, MAD-ATH 2.370 km.
SEDES = pd.DataFrame({
    "id": [10, 20, 30],
    "lat": [40.4239, 41.3800, 37.9838],
    "lon": [-3.6718, 2.1201, 23.7275],
})


def _games(rows):
    cols = ["id", "competicion_id", "temporada_id", "fecha", "hora_utc", "local_id", "visitante_id",
            "sede_id", "jugado", "pts_local", "pts_visitante"]
    return pd.DataFrame(rows, columns=cols)


GAMES = _games([
    ("g1", "ACB", 2025, "2025-10-01", None, 1, 2, 10, 1, 90, 80),   # Madrid recibe a Barcelona
    ("g2", "E", 2025, "2025-10-03", "2025-10-03T18:00:00", 3, 1, 30, 1, 70, 75),  # Madrid viaja a Atenas
    ("g3", "ACB", 2025, "2025-10-09", None, 2, 1, 20, 1, 85, 85),   # Madrid viaja a Barcelona
    ("g4", "E", 2025, "2025-10-20", None, 1, 3, 10, 0, None, None),  # sin jugar: se ignora
])


@pytest.fixture()
def cg():
    return build_club_games(GAMES, SEDES)


def _row(df, game, club):
    return df[(df.partido_id == game) & (df.club_id == club)].iloc[0]


def test_club_games_has_two_rows_per_played_game_and_ignores_unplayed(cg):
    assert len(cg) == 6
    assert "g4" not in set(cg.partido_id)


def test_club_games_points_and_result(cg):
    r = _row(cg, "g2", 1)
    assert (r.pts_for, r.pts_against, r.margin, r.win, r.home) == (75, 70, 5, 1, 0)
    assert _row(cg, "g3", 1).win == 0.5  # empate: no ocurre en baloncesto, pero no debe romper


def test_rest_days_and_first_game(cg):
    out = add_rest_and_travel(cg, SEDES)
    assert pd.isna(_row(out, "g1", 1).rest_days)
    assert _row(out, "g2", 1).rest_days == 2
    assert _row(out, "g3", 1).rest_days == 6


def test_trip_km_is_zero_at_home_and_round_trip_away(cg):
    out = add_rest_and_travel(cg, SEDES)
    assert _row(out, "g1", 1).km_trip == 0
    assert _row(out, "g2", 1).km_trip == pytest.approx(2 * 2370, rel=0.02)
    assert _row(out, "g3", 1).km_trip == pytest.approx(2 * 505, rel=0.02)


def test_km_prev_chains_from_previous_venue(cg):
    out = add_rest_and_travel(cg, SEDES)
    assert pd.isna(_row(out, "g1", 1).km_prev)
    assert _row(out, "g2", 1).km_prev == pytest.approx(2370, rel=0.02)
    assert _row(out, "g3", 1).km_prev == pytest.approx(1885, rel=0.01)  # Atenas -> Barcelona (cálculo a mano: ~378 km N-S y ~1.850 km E-O)


def test_rolling_km_includes_current_game_and_respects_window(cg):
    out = add_rest_and_travel(cg, SEDES)
    g3 = _row(out, "g3", 1)
    # g2 (6 días antes) cae dentro de 7 días; g1 no aporta km.
    assert g3.km_7d == pytest.approx(g3.km_trip + _row(out, "g2", 1).km_trip)
    assert g3.games_prev_7d == 1


def test_rolling_window_excludes_old_games():
    games = _games([
        ("a", "E", 2025, "2025-10-01", None, 1, 3, 30, 1, 1, 2),
        ("b", "E", 2025, "2025-10-20", None, 1, 2, 20, 1, 1, 2),
    ])
    out = add_rest_and_travel(build_club_games(games, SEDES), SEDES)
    b = _row(out, "b", 1)
    assert b.km_7d == pytest.approx(b.km_trip)
    assert b.km_14d == pytest.approx(b.km_trip)
    assert b.games_prev_7d == 0


def test_rest_days_do_not_cross_seasons():
    games = _games([
        ("a", "E", 2024, "2025-05-01", None, 1, 2, 10, 1, 1, 2),
        ("b", "E", 2025, "2025-10-01", None, 1, 2, 10, 1, 1, 2),
    ])
    out = add_rest_and_travel(build_club_games(games, SEDES), SEDES)
    assert out.rest_days.isna().all()


MINUTES = pd.DataFrame({
    "partido_id": ["g1"] * 7,
    "club_id": [1] * 7,
    "jugador": list("ABCDEFG"),
    "titular": [1, 1, 1, 1, 1, 0, 0],
    "minutos": [30.0, 30.0, 30.0, 30.0, 30.0, 25.0, 25.0],
})


def test_rotation_metrics(cg):
    out = add_rotation(cg, MINUTES)
    r = _row(out, "g1", 1)
    assert r.players_used == 7
    assert r.players_10 == 7
    assert r.top5_share == pytest.approx(150 / 200)
    assert r.hhi == pytest.approx(5 * (30 / 200) ** 2 + 2 * (25 / 200) ** 2)
    assert pd.isna(_row(out, "g1", 2).players_used)  # sin minutos


def test_starters_changed_vs_previous_game():
    games = _games([
        ("g1", "ACB", 2025, "2025-10-01", None, 1, 2, 10, 1, 90, 80),
        ("g2", "ACB", 2025, "2025-10-05", None, 1, 2, 10, 1, 90, 80),
    ])
    minutes = pd.DataFrame({
        "partido_id": ["g1"] * 6 + ["g2"] * 6,
        "club_id": [1] * 12,
        "jugador": list("ABCDEF") * 2,
        "titular": [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1],  # en g2 sale E y entra F
        "minutos": [20.0] * 12,
    })
    out = add_rotation(build_club_games(games, SEDES), minutes)
    assert pd.isna(_row(out, "g1", 1).starters_changed)
    assert _row(out, "g2", 1).starters_changed == 1


def test_adjusted_margin_is_zero_sum_per_game_and_rewards_overperformance():
    # El club 1 gana siempre por 10 en casa y fuera; el 2 y el 3 empatan entre sí.
    rows, n = [], 0
    for _ in range(6):
        for h, a, ph, pa in [(1, 2, 90, 80), (2, 1, 80, 90), (1, 3, 90, 80), (3, 1, 80, 90), (2, 3, 80, 80), (3, 2, 80, 80)]:
            n += 1
            rows.append((f"x{n}", "E", 2025, f"2025-10-{n % 28 + 1:02d}", None, h, a, 10, 1, ph, pa))
    out = add_adjusted_margin(build_club_games(_games(rows), SEDES))
    one = out[out.club_id == 1]
    assert one.margin_resid.abs().max() < 1.5  # el modelo ya espera que gane por ~10
    g = out[out.partido_id == "x1"]
    assert g.margin_resid.sum() == pytest.approx(0, abs=1e-9)


def test_build_metrics_returns_all_columns(cg):
    out = build_metrics(GAMES, SEDES, MINUTES)
    for col in ("rest_days", "km_trip", "km_7d", "km_14d", "players_10", "top5_share", "margin_resid"):
        assert col in out.columns
    assert len(out) == 6
