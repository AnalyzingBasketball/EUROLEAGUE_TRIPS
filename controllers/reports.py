"""Montaje de los informes PDF de cada página a partir de los datos ya filtrados."""
import pandas as pd

from common.pdf_generator import Image, Table, build_report
from controllers.chart_data import binned_effect
from controllers.mpl_charts import effect_png, km_by_club_png, venue_map_png

CAVEAT = "Las gráficas muestran correlaciones, no causas."


def trip_report(user: str, filters: dict[str, str], trips: pd.DataFrame, km: pd.DataFrame | None,
                venues: pd.DataFrame, lines: pd.DataFrame | None) -> bytes:
    """Informe de la página Calendario y viajes."""
    blocks: list[Table | Image] = [Table("Partidos jugados y kilómetros", trips)]
    if km is not None and not km.empty:
        blocks.append(Image("Km de viaje acumulados por club", km_by_club_png(km), "Ida y vuelta entre la sede base y la del partido."))
    if not venues.empty:
        blocks.append(Image("Sedes de los partidos", venue_map_png(venues, lines)))
    return build_report("Calendario y viajes", user, filters, blocks)


def fatigue_report(user: str, filters: dict[str, str], table: pd.DataFrame, scope: pd.DataFrame,
                   rotation_key: str, rotation_label: str) -> bytes:
    """Informe de la página Fatiga y rotaciones; `scope` son las métricas de todas las temporadas filtradas."""
    blocks: list[Table | Image] = [Table("Descanso, carga y rotación por partido", table)]
    if not scope.empty:
        rest = binned_effect(scope, "rest_days", "margin_resid")
        blocks.append(Image("Rendimiento según el descanso", effect_png(rest, "Margen ajustado medio (puntos)", "Días desde el partido anterior"),
                            "Media por tramo con ±1,96 errores estándar. " + CAVEAT))
        rot = binned_effect(scope, "km_7d", rotation_key)
        blocks.append(Image(f"{rotation_label} según los km de los últimos 7 días",
                            effect_png(rot, rotation_label, "Km de viaje acumulados en 7 días"), CAVEAT))
    return build_report("Fatiga y rotaciones", user, filters, blocks)
