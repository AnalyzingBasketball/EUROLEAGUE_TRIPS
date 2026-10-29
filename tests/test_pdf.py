import numpy as np
import pandas as pd

from common.pdf_generator import Image, Table, build_report
from controllers.mpl_charts import effect_png, km_by_club_png, venue_map_png
from controllers.reports import fatigue_report, trip_report

PNG = b"\x89PNG"


def _pages(pdf: bytes) -> int:
    return pdf.count(b"/Type /Page\n") or pdf.count(b"/Type /Page ") or pdf.count(b"/Type/Page")


def test_km_png_is_png():
    data = pd.DataFrame({"Club": ["A", "A", "B"], "Competición": ["ACB", "E", "E"], "Km": [10.0, 20.0, 5.0]})
    assert km_by_club_png(data).startswith(PNG)


def test_effect_png_handles_missing_competition_in_a_bin():
    data = pd.DataFrame({"tramo": ["a", "b", "a"], "competicion_id": ["ACB", "ACB", "E"], "media": [1.0, 2.0, 3.0],
                         "n": [5, 6, 7], "se": [0.5, 0.2, 0.1]})
    assert effect_png(data, "y", "x").startswith(PNG)


def test_venue_map_png_with_and_without_lines():
    venues = pd.DataFrame({"nombre": ["A"], "pais": ["es"], "lat": [40.0], "lon": [-3.0], "partidos": [3], "revisar": [0]})
    lines = pd.DataFrame({"base_lat": [40.0], "base_lon": [-3.0], "destino_lat": [38.0], "destino_lon": [23.0]})
    assert venue_map_png(venues, lines).startswith(PNG)
    assert venue_map_png(venues, None).startswith(PNG)


def test_report_with_accents_symbols_and_nan():
    df = pd.DataFrame({"Descanso (días)": [2.0, np.nan], "Jugadores ≥10 min": [9, 8], "Club": ["Río Breogán", "Bàsquet Girona"]})
    pdf = build_report("Fatiga ñandú", "admin", {"Temporada": "2025/26"}, [Table("Tabla ±", df)])
    assert pdf.startswith(b"%PDF")


def test_report_truncates_long_tables_and_adds_pages():
    df = pd.DataFrame({"a": range(300), "b": ["x" * 80] * 300})
    pdf = build_report("T", "admin", {}, [Table("Larga", df, max_rows=250)])
    assert _pages(pdf) > 1


def test_report_with_empty_table():
    assert build_report("T", "admin", {}, [Table("Vacía", pd.DataFrame())]).startswith(b"%PDF")


def test_report_with_image():
    data = pd.DataFrame({"Club": ["A"], "Competición": ["ACB"], "Km": [1.0]})
    pdf = build_report("T", "admin", {}, [Image("g", km_by_club_png(data), "nota")])
    assert b"/Subtype /Image" in pdf or b"/Subtype/Image" in pdf


def test_trip_and_fatigue_reports_build():
    trips = pd.DataFrame({"Club": ["A"], "Km": [1.0]})
    venues = pd.DataFrame({"nombre": ["A"], "pais": ["es"], "lat": [40.0], "lon": [-3.0], "partidos": [3], "revisar": [0]})
    km = pd.DataFrame({"Club": ["A"], "Competición": ["E"], "Km": [1.0]})
    assert trip_report("admin", {}, trips, km, venues, None).startswith(b"%PDF")
    scope = pd.DataFrame({"competicion_id": ["E", "E"], "rest_days": [2.0, 6.0], "km_7d": [0.0, 500.0],
                          "margin_resid": [1.0, -1.0], "players_10": [9, 10], "home": [1, 0], "win": [1.0, 0.0],
                          "margin": [5.0, -5.0], "km_trip": [0.0, 800.0]})
    pdf = fatigue_report("admin", {}, trips, scope, "players_10", "Jugadores ≥10 min")
    assert pdf.startswith(b"%PDF")
    assert _pages(pdf) >= 2
    assert fatigue_report("admin", {}, trips, scope, "players_10", "x", "margin_resid", "trip_hours").startswith(b"%PDF")
    assert fatigue_report("admin", {}, trips, scope.iloc[0:0], "players_10", "x").startswith(b"%PDF")
