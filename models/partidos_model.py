"""Lectura de partidos, sedes y minutos desde SQLite; devuelve DataFrames sin lógica de negocio."""
import sqlite3

import pandas as pd


def load_games(conn: sqlite3.Connection) -> pd.DataFrame:
    """Todos los partidos con nombres de club y competición."""
    return pd.read_sql_query(
        "SELECT p.id, p.competicion_id, p.temporada_id, p.fecha, p.hora_utc, p.jornada, p.fase, p.local_id,"
        " p.visitante_id, p.sede_id, p.neutral, p.jugado, p.pts_local, p.pts_visitante FROM partido p",
        conn,
    )


def load_venues(conn: sqlite3.Connection) -> pd.DataFrame:
    """Sedes con coordenadas y marca de revisión."""
    return pd.read_sql_query("SELECT id, nombre, pais, lat, lon, precision, revisar FROM sede", conn)


def load_clubs(conn: sqlite3.Connection) -> pd.DataFrame:
    """Clubes y las competiciones en las que juegan cada temporada."""
    return pd.read_sql_query(
        "SELECT c.id AS club_id, c.nombre AS club, ct.temporada_id, ct.competicion_id"
        " FROM club c JOIN club_temporada ct ON ct.club_id = c.id",
        conn,
    )


def load_minutes(conn: sqlite3.Connection) -> pd.DataFrame:
    """Minutos por jugador y partido."""
    return pd.read_sql_query(
        "SELECT partido_id, club_id, jugador, titular, minutos, puntos FROM minutos_jugador", conn
    )
