import sqlite3

import pytest

from models.db import connect, create_schema, season_label

TABLES = {
    "competicion", "temporada", "club", "club_alias", "club_temporada",
    "sede", "sede_alias", "club_pabellon", "partido", "minutos_jugador",
}


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.db")
    create_schema(c)
    yield c
    c.close()


def _seed_two_clubs(conn):
    conn.executemany("INSERT INTO club (id, nombre) VALUES (?, ?)", [(1, "A"), (2, "B")])
    conn.commit()


def test_season_label():
    assert season_label(2025) == "2025/26"
    assert season_label(2099) == "2099/00"


def test_creates_all_tables(conn):
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= names


def test_seeds_competitions_and_seasons(conn):
    assert [r["id"] for r in conn.execute("SELECT id FROM competicion ORDER BY id")] == ["ACB", "E", "U"]
    assert conn.execute("SELECT COUNT(*) FROM temporada").fetchone()[0] == 5


def test_create_schema_is_idempotent(conn):
    create_schema(conn)
    assert conn.execute("SELECT COUNT(*) FROM competicion").fetchone()[0] == 3


def test_partido_rejects_same_home_and_away(conn):
    _seed_two_clubs(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO partido (id, competicion_id, temporada_id, fecha, local_id, visitante_id)"
            " VALUES ('E-2025-1', 'E', 2025, '2025-10-01T18:00:00', 1, 1)"
        )


def test_partido_rejects_unknown_club(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO partido (id, competicion_id, temporada_id, fecha, local_id, visitante_id)"
            " VALUES ('E-2025-1', 'E', 2025, '2025-10-01T18:00:00', 98, 99)"
        )


def test_alias_unique_per_competition_code_and_season(conn):
    _seed_two_clubs(conn)
    sql = (
        "INSERT INTO club_alias (club_id, competicion_id, codigo, temporada_desde)"
        " VALUES (?, 'E', 'BAR', 2022)"
    )
    conn.execute(sql, (1,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, (2,))


def test_sede_rejects_invalid_coordinates(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO sede (nombre, lat, lon, precision) VALUES ('X', 95, 0, 'calle')"
        )


def test_sede_rejects_unknown_precision(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO sede (nombre, lat, lon, precision) VALUES ('X', 40, 0, 'aprox')"
        )


def test_club_can_play_two_competitions_same_season(conn):
    _seed_two_clubs(conn)
    conn.executemany(
        "INSERT INTO club_temporada VALUES (?, ?, ?)",
        [(1, 2025, "E"), (1, 2025, "ACB")],
    )
    n = conn.execute(
        "SELECT COUNT(DISTINCT competicion_id) FROM club_temporada WHERE club_id = 1 AND temporada_id = 2025"
    ).fetchone()[0]
    assert n == 2


def test_read_only_connection_blocks_writes(tmp_path):
    path = tmp_path / "ro.db"
    c = connect(path)
    create_schema(c)
    c.close()
    ro = connect(path, read_only=True)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO club (nombre) VALUES ('X')")
    ro.close()
