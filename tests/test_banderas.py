import sqlite3
from pathlib import Path

import pandas as pd
from PIL import Image

from controllers.labels import COUNTRY_NAMES
from controllers.views import add_flags, trip_table, venues_table

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "assets" / "banderas"


def test_every_venue_country_has_a_flag_file_and_a_name():
    conn = sqlite3.connect(ROOT / "data" / "viajes_fatiga.db")
    countries = {row[0] for row in conn.execute("SELECT DISTINCT pais FROM sede")}
    assert countries <= {path.stem for path in FOLDER.glob("*.png")}
    assert countries <= set(COUNTRY_NAMES)


def test_flag_files_are_small_png():
    for path in FOLDER.glob("*.png"):
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert max(img.size) <= 128


def test_add_flags_inserts_the_column_before_country():
    table = pd.DataFrame({"Ciudad": ["Madrid", "París"], "País": ["España", "Francia"]})
    out = add_flags(table, pd.Series(["es", "fr"]), {"es": "data:es", "fr": "data:fr"})
    assert list(out.columns) == ["Ciudad", "Bandera", "País"]
    assert list(out["Bandera"]) == ["data:es", "data:fr"]


def test_add_flags_without_flags_leaves_the_table_alone():
    table = pd.DataFrame({"País": ["España"]})
    assert list(add_flags(table, pd.Series(["es"]), None).columns) == ["País"]


def test_venues_table_flag_follows_each_row_country():
    venues = pd.DataFrame({
        "id": [1, 2], "nombre": ["A", "B"], "ciudad": ["X", "Y"], "pais": ["es", "tr"], "lat": [0.0, 0.0],
        "lon": [0.0, 0.0], "precision": ["pabellon", "ciudad"], "revisar": [0, 1],
    })
    out = venues_table(venues, {"es": "data:es", "tr": "data:tr"})
    assert list(out["Bandera"]) == ["data:es", "data:tr"]
    assert list(out["País"]) == ["España", "Turquía"]


def test_trip_table_flag_is_the_country_of_the_match_venue():
    metrics = pd.DataFrame({
        "fecha": pd.to_datetime(["2025-10-01", "2025-10-02"]), "competicion_id": ["E", "E"], "club_id": [1, 2],
        "rival_id": [2, 1], "home": [1, 0], "sede_id": [10, 10], "pts_for": [80, 70], "pts_against": [70, 80],
        "rest_days": [3.0, 4.0], "km_trip": [0.0, 100.0], "km_prev": [0.0, 100.0], "km_7d": [0.0, 100.0],
        "km_14d": [0.0, 100.0],
    })
    venues = pd.DataFrame({"id": [10], "nombre": ["Pabellón"], "ciudad": ["Estambul"], "pais": ["tr"]})
    out = trip_table(metrics, {1: "A", 2: "B"}, venues, flags={"tr": "data:tr"})
    assert list(out["Bandera"]) == ["data:tr", "data:tr"]
    assert list(out["País"]) == ["Turquía", "Turquía"]
