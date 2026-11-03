"""Montaje de los informes PDF de cada página a partir de los datos ya filtrados."""
import pandas as pd

from common.pdf_generator import Image, Table, build_report
from controllers.chart_data import (
    RESULT_MEASURES,
    TRIP_UNITS,
    add_result_columns,
    away_trip_effect,
    binned_effect,
    home_away_effect,
    rest_trip_grid,
)
from controllers.mpl_charts import (
    effect_png,
    km_by_club_png,
    rest_trip_heatmap_png,
    venue_map_png,
)

CAVEAT = "Las gráficas muestran correlaciones, no causas. Se omiten los tramos con menos de 5 partidos."


def trip_report(user: str, filters: dict[str, str], trips: pd.DataFrame, km: pd.DataFrame | None,
                venues: pd.DataFrame, lines: pd.DataFrame | None) -> bytes:
    """Informe de la página Calendario y viajes."""
    blocks: list[Table | Image] = [Table("Partidos jugados y kilómetros", trips)]
    if km is not None and not km.empty:
        blocks.append(Image("Km de viaje acumulados por club", km_by_club_png(km), "Ida y vuelta entre la sede base y la del partido."))
    if not venues.empty:
        blocks.append(Image("Sedes de los partidos", venue_map_png(venues, lines)))
    return build_report("Calendario y viajes", user, filters, blocks)


def _effect_block(title: str, data: pd.DataFrame, y_title: str, x_title: str, note: str) -> list[Image]:
    """Un bloque de gráfica de efecto; vacío si no queda ningún tramo con suficientes partidos."""
    return [Image(title, effect_png(data, y_title, x_title), note)] if not data.empty else []


def result_blocks(scope: pd.DataFrame, measure: str, unit: str) -> list[Table | Image]:
    """Gráficas de resultados y viaje; `scope` debe llevar las columnas de `add_result_columns`."""
    label = RESULT_MEASURES[measure]
    scope = add_result_columns(scope)
    away = scope[scope["home"] == 0]
    blocks: list[Table | Image] = list(_effect_block(
        "Victorias en casa y fuera", home_away_effect(scope, "win_pct"), "Victorias (%)", "Condición del partido",
        "Media con ±1,96 errores estándar. " + CAVEAT,
    ))
    if not away.empty:
        blocks += _effect_block(
            f"{label} fuera de casa según el viaje", away_trip_effect(scope, unit, measure), label, TRIP_UNITS[unit],
            "Solo partidos fuera. Las horas son una estimación (autobús o avión con 3 h de aeropuerto). " + CAVEAT,
        )
        blocks.append(Image(
            f"{label} fuera de casa según descanso y viaje",
            rest_trip_heatmap_png(rest_trip_grid(scope, measure), label, float(away[measure].mean())),
            f"Color respecto a la media de los partidos fuera ({round(away[measure].mean(), 1) + 0.0:.1f}). "
            "Celdas con menos de 15 partidos en blanco. " + CAVEAT,
        ))
    return blocks


def fatigue_report(user: str, filters: dict[str, str], table: pd.DataFrame, scope: pd.DataFrame,
                   rotation_key: str, rotation_label: str, measure: str = "win_pct", unit: str = "km_trip") -> bytes:
    """Informe de la página Fatiga y rotaciones; `scope` son las métricas de todas las temporadas filtradas."""
    blocks: list[Table | Image] = [Table("Descanso, carga y rotación por partido", table)]
    if not scope.empty:
        blocks += _effect_block(
            "Rendimiento según el descanso", binned_effect(scope, "rest_days", "margin_resid"),
            "Margen ajustado medio (puntos)", "Días desde el partido anterior",
            "Media por tramo con ±1,96 errores estándar. " + CAVEAT,
        )
        blocks += _effect_block(
            f"{rotation_label} según los km de los últimos 7 días", binned_effect(scope, "km_7d", rotation_key),
            rotation_label, "Km de viaje acumulados en 7 días", CAVEAT,
        )
        blocks.extend(result_blocks(scope, measure, unit))
    return build_report("Fatiga y rotaciones", user, filters, blocks)
