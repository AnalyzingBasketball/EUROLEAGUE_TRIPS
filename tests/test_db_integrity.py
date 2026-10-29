"""Comprobaciones sobre la base construida; se omiten si aún no existe data/viajes_fatiga.db."""
import pytest

from models.db import DEFAULT_DB_PATH, connect

pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason="base no construida")


@pytest.fixture(scope="module")
def conn():
    c = connect(DEFAULT_DB_PATH, read_only=True)
    yield c
    c.close()


def _one(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_foreign_keys_hold(conn):
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_every_game_has_venue(conn):
    assert _one(conn, "SELECT COUNT(*) FROM partido WHERE sede_id IS NULL") == 0


def test_played_games_have_scores(conn):
    assert _one(conn, "SELECT COUNT(*) FROM partido WHERE jugado = 1 AND (pts_local IS NULL OR pts_visitante IS NULL)") == 0


def test_unplayed_games_have_no_scores(conn):
    assert _one(conn, "SELECT COUNT(*) FROM partido WHERE jugado = 0 AND pts_local IS NOT NULL") == 0


def test_all_three_competitions_present(conn):
    rows = {r[0] for r in conn.execute("SELECT DISTINCT competicion_id FROM partido")}
    assert rows == {"E", "U", "ACB"}


def test_dual_competition_clubs_exist(conn):
    n = _one(conn, """SELECT COUNT(*) FROM (SELECT club_id, temporada_id FROM club_temporada
                      GROUP BY club_id, temporada_id HAVING COUNT(DISTINCT competicion_id) >= 2)""")
    assert n > 0


def test_club_alias_has_no_overlapping_names_for_same_code(conn):
    dup = conn.execute("""SELECT competicion_id, codigo, temporada_desde FROM club_alias
                          GROUP BY 1, 2, 3 HAVING COUNT(*) > 1""").fetchall()
    assert dup == []


def test_valencia_changes_arena_in_acb(conn):
    rows = {r[0] for r in conn.execute("""SELECT DISTINCT s.nombre FROM partido p JOIN club c ON c.id = p.local_id
                                          JOIN sede s ON s.id = p.sede_id
                                          WHERE c.nombre = 'Valencia Basket' AND p.competicion_id = 'ACB'""")}
    assert len(rows) == 2


def test_minutes_sum_close_to_game_length(conn):
    # 400 min en 40 de juego (+50 por prórroga); hay partidos con 3 prórrogas y uno con minutos incompletos en la fuente (380).
    bad = _one(conn, """SELECT COUNT(*) FROM (SELECT partido_id, SUM(minutos) m FROM minutos_jugador
                        GROUP BY partido_id HAVING m < 375 OR m > 650)""")
    assert bad == 0


@pytest.fixture(scope="module")
def metrics(conn):
    from controllers.metrics import build_metrics
    from models.partidos_model import load_games, load_minutes, load_venues

    return build_metrics(load_games(conn), load_venues(conn), load_minutes(conn))


def test_metrics_two_rows_per_played_game(metrics, conn):
    assert len(metrics) == 2 * _one(conn, "SELECT COUNT(*) FROM partido WHERE jugado = 1")


def test_metrics_ranges(metrics):
    assert (metrics["rest_days"].dropna() >= 0).all()
    assert (metrics["km_trip"] >= 0).all()
    assert (metrics.loc[metrics["home"] == 1, "km_trip"] == 0).all()
    assert (metrics["km_14d"] >= metrics["km_7d"] - 1e-9).all()


def test_metrics_residuals_sum_to_zero_per_game(metrics):
    assert metrics.groupby("partido_id")["margin_resid"].sum().abs().max() < 1e-6
