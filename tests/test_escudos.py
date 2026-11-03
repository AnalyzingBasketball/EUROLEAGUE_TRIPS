import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from controllers.views import add_crests

ROOT = Path(__file__).resolve().parent.parent
INDEX = pd.read_csv(ROOT / "data" / "escudos.csv")
FOLDER = ROOT / "assets" / "escudos"


def test_every_club_in_the_database_has_a_crest_entry():
    conn = sqlite3.connect(ROOT / "data" / "viajes_fatiga.db")
    clubs = {row[0] for row in conn.execute("SELECT nombre FROM club")}
    assert clubs == set(INDEX["club"])


def test_crest_files_exist_are_png_and_small():
    assert INDEX["archivo"].is_unique
    for name in INDEX["archivo"]:
        with Image.open(FOLDER / name) as img:
            assert img.format == "PNG"
            assert max(img.size) <= 128


def test_index_names_the_source_of_each_crest():
    assert set(INDEX["fuente"]) == {"API de Euroliga", "acb.com"}
    assert INDEX["url_origen"].str.startswith("https://").all()


def test_add_crests_inserts_columns_before_club_and_rival():
    table = pd.DataFrame({"Fecha": [1], "Club": ["A"], "Rival": ["B"]})
    out = add_crests(table, {"A": "x/a.png", "B": "x/b.png"})
    assert list(out.columns) == ["Fecha", "Escudo", "Club", "Escudo rival", "Rival"]
    assert out.loc[0, "Escudo"] == "x/a.png" and out.loc[0, "Escudo rival"] == "x/b.png"


@pytest.mark.parametrize("crests", [None, {}])
def test_add_crests_without_crests_leaves_the_table_alone(crests):
    table = pd.DataFrame({"Club": ["A"], "Rival": ["B"]})
    assert list(add_crests(table, crests).columns) == ["Club", "Rival"]
