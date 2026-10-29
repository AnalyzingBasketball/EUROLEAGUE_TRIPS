"""Tablas de presentación: filtran y renombran las métricas para mostrarlas."""
import pandas as pd

from controllers.charts import COMP_NAMES
from controllers.labels import country_name

PRECISION_NAMES = {"pabellon": "Pabellón", "calle": "Calle", "ciudad": "Ciudad"}


def competition_names(df: pd.DataFrame, column: str = "competicion_id") -> pd.DataFrame:
    """Copia de la tabla con la competición por su nombre (ACB, Euroliga, EuroCup) en una columna «Competición»."""
    out = df.copy()
    out[column] = out[column].map(COMP_NAMES).fillna(out[column])
    return out.rename(columns={column: "Competición"})


def venues_table(venues: pd.DataFrame) -> pd.DataFrame:
    """Catálogo de sedes con nombres de columna y país en español, listo para mostrar."""
    return pd.DataFrame({
        "Id": venues["id"], "Sede": venues["nombre"], "Ciudad": venues["ciudad"], "País": venues["pais"].map(country_name),
        "Latitud": venues["lat"], "Longitud": venues["lon"],
        "Precisión": venues["precision"].map(PRECISION_NAMES).fillna(venues["precision"]),
        "Revisar": venues["revisar"].map({0: "No", 1: "Sí"}),
    })


def club_names(clubs: pd.DataFrame) -> dict[int, str]:
    """Mapa id -> nombre de club."""
    return dict(zip(clubs["club_id"], clubs["club"], strict=False))


def seasons_label(season: int) -> str:
    """2025 -> '2025/26'."""
    return f"{season}/{str(season + 1)[-2:]}"


def filter_metrics(
    metrics: pd.DataFrame, season: int, competitions: list[str], club_id: int | None = None
) -> pd.DataFrame:
    """Filas de una temporada, de las competiciones elegidas y, si se indica, de un club."""
    out = metrics[(metrics["temporada_id"] == season) & (metrics["competicion_id"].isin(competitions))]
    if club_id is not None:
        out = out[out["club_id"] == club_id]
    return out


def _whole(values: pd.Series) -> pd.Series:
    """Redondea a enteros y deja los huecos como NaN: Streamlit los pinta en blanco (con Int64 saldría «None»)."""
    return values.round(0)


def trip_table(metrics: pd.DataFrame, names: dict[int, str], venues: pd.DataFrame) -> pd.DataFrame:
    """Calendario con descanso y km, listo para mostrar."""
    sedes = venues.set_index("id")
    out = pd.DataFrame({
        "Fecha": metrics["fecha"].dt.date,
        "Competición": metrics["competicion_id"].map(COMP_NAMES),
        "Club": metrics["club_id"].map(names),
        "Rival": metrics["rival_id"].map(names),
        "Condición": metrics["home"].map({1: "Local", 0: "Visitante"}),
        "Sede": metrics["sede_id"].map(sedes["nombre"]),
        "Ciudad": metrics["sede_id"].map(sedes["ciudad"]),
        "País": metrics["sede_id"].map(sedes["pais"]).map(country_name),
        "Resultado": metrics["pts_for"].astype(int).astype(str) + "-" + metrics["pts_against"].astype(int).astype(str),
        "Descanso (días)": _whole(metrics["rest_days"]),
        "Km del viaje": _whole(metrics["km_trip"]),
        "Km desde la sede anterior": _whole(metrics["km_prev"]),
        "Km 7 días": _whole(metrics["km_7d"]),
        "Km 14 días": _whole(metrics["km_14d"]),
    })
    return out.sort_values(["Fecha", "Club"]).reset_index(drop=True)


def fatigue_table(metrics: pd.DataFrame, names: dict[int, str]) -> pd.DataFrame:
    """Descanso, carga y rotación por partido, listo para mostrar."""
    out = pd.DataFrame({
        "Fecha": metrics["fecha"].dt.date,
        "Competición": metrics["competicion_id"].map(COMP_NAMES),
        "Club": metrics["club_id"].map(names),
        "Rival": metrics["rival_id"].map(names),
        "Descanso (días)": _whole(metrics["rest_days"]),
        "Partidos 7 días previos": _whole(metrics["games_prev_7d"]),
        "Km 7 días": _whole(metrics["km_7d"]),
        "Jugadores ≥10 min": _whole(metrics["players_10"]),
        "Cuota de minutos top 5": (metrics["top5_share"] * 100).round(1),
        "Titulares cambiados": _whole(metrics["starters_changed"]),
        "Margen": _whole(metrics["margin"]),
        "Margen ajustado": metrics["margin_resid"].round(1),
    })
    return out.sort_values(["Fecha", "Club"]).reset_index(drop=True)


def upcoming_games(live: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """Próximos partidos sin jugar de la API, ordenados por fecha."""
    pending = live[live["jugado"] == 0].sort_values(["fecha", "hora_utc"]).head(limit)
    return pd.DataFrame({
        "Fecha": pending["fecha"],
        "Hora UTC": pending["hora_utc"].fillna("").str[11:16],
        "Jornada": pending["jornada"],
        "Local": pending["local_name"],
        "Visitante": pending["road_name"],
    }).reset_index(drop=True)
