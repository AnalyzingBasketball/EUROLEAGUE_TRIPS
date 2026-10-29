"""Acceso a la base SQLite: creación del esquema y conexiones."""
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "viajes_fatiga.db"

COMPETICIONES: dict[str, str] = {
    "E": "Euroliga",
    "U": "EuroCup",
    "ACB": "Liga Endesa",
}


def season_label(season: int) -> str:
    """Devuelve la etiqueta de temporada: 2025 -> '2025/26'."""
    return f"{season}/{str(season + 1)[-2:]}"


def connect(db_path: Path = DEFAULT_DB_PATH, read_only: bool = False) -> sqlite3.Connection:
    """Abre la base con claves foráneas activas; en modo solo lectura para la app publicada."""
    if read_only:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection, seasons: range = range(2022, 2027)) -> None:
    """Crea las tablas y carga competiciones y temporadas."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executemany(
        "INSERT OR IGNORE INTO competicion (id, nombre) VALUES (?, ?)",
        COMPETICIONES.items(),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO temporada (id, etiqueta) VALUES (?, ?)",
        [(s, season_label(s)) for s in seasons],
    )
    conn.commit()
