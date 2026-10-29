"""Tablas de presentación: filtran y renombran las métricas para mostrarlas."""
import pandas as pd


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


def trip_table(metrics: pd.DataFrame, names: dict[int, str], venues: pd.DataFrame) -> pd.DataFrame:
    """Calendario con descanso y km, listo para mostrar."""
    sedes = venues.set_index("id")["nombre"]
    out = pd.DataFrame({
        "Fecha": metrics["fecha"].dt.date,
        "Competición": metrics["competicion_id"],
        "Club": metrics["club_id"].map(names),
        "Rival": metrics["rival_id"].map(names),
        "Condición": metrics["home"].map({1: "Local", 0: "Visitante"}),
        "Sede": metrics["sede_id"].map(sedes),
        "Resultado": metrics["pts_for"].astype(int).astype(str) + "-" + metrics["pts_against"].astype(int).astype(str),
        "Descanso (días)": metrics["rest_days"],
        "Km del viaje": metrics["km_trip"].round(0),
        "Km desde la sede anterior": metrics["km_prev"].round(0),
        "Km 7 días": metrics["km_7d"].round(0),
        "Km 14 días": metrics["km_14d"].round(0),
    })
    return out.sort_values(["Fecha", "Club"]).reset_index(drop=True)


def fatigue_table(metrics: pd.DataFrame, names: dict[int, str]) -> pd.DataFrame:
    """Descanso, carga y rotación por partido, listo para mostrar."""
    out = pd.DataFrame({
        "Fecha": metrics["fecha"].dt.date,
        "Competición": metrics["competicion_id"],
        "Club": metrics["club_id"].map(names),
        "Rival": metrics["rival_id"].map(names),
        "Descanso (días)": metrics["rest_days"],
        "Partidos 7 días previos": metrics["games_prev_7d"],
        "Km 7 días": metrics["km_7d"].round(0),
        "Jugadores ≥10 min": metrics["players_10"],
        "Cuota de minutos top 5": (metrics["top5_share"] * 100).round(1),
        "Titulares cambiados": metrics["starters_changed"],
        "Margen": metrics["margin"],
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
