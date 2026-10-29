"""Datos agregados para los gráficos. Funciones puras: DataFrame entra, DataFrame sale."""
import numpy as np
import pandas as pd

REST_BINS = [0, 2, 3, 5, 7, np.inf]
REST_LABELS = ["2 días o menos", "3 días", "4-5 días", "6-7 días", "8 días o más"]
KM_BINS = [-1, 0, 1000, 3000, np.inf]
KM_LABELS = ["Sin viaje (0 km)", "1-1.000 km", "1.000-3.000 km", "Más de 3.000 km"]

KM_TRIP_BINS = [-1, 500, 1000, 2000, 3000, np.inf]
KM_TRIP_LABELS = ["Hasta 500 km", "500-1.000 km", "1.000-2.000 km", "2.000-3.000 km", "Más de 3.000 km"]
HOURS_BINS = [-1, 6, 9, 12, 15, np.inf]
HOURS_LABELS = ["Hasta 6 h", "6-9 h", "9-12 h", "12-15 h", "Más de 15 h"]

BINS = {
    "rest_days": (REST_BINS, REST_LABELS),
    "km_7d": (KM_BINS, KM_LABELS),
    "km_trip": (KM_TRIP_BINS, KM_TRIP_LABELS),
    "trip_hours": (HOURS_BINS, HOURS_LABELS),
}

RESULT_MEASURES = {"win_pct": "Victorias (%)", "margin": "Margen (puntos)", "margin_resid": "Margen ajustado (puntos)"}
TRIP_UNITS = {"km_trip": "Km del viaje (ida y vuelta)", "trip_hours": "Horas de viaje aproximadas (ida y vuelta)"}
MIN_CELL = 15  # partidos mínimos para colorear una celda del mapa de calor

# Estimación del tiempo de viaje: el mejor de autobús o avión (con 3 h de aeropuerto) para la mitad del trayecto.
BUS_KMH, FLIGHT_KMH, AIRPORT_HOURS = 75.0, 750.0, 3.0


def default_season(metrics: pd.DataFrame) -> int:
    """Temporada más reciente con al menos la mitad de partidos que la más completa (evita abrir en una en curso)."""
    counts = metrics.groupby("temporada_id")["partido_id"].nunique()
    return int(counts[counts >= counts.max() / 2].index.max())


def mark_dual(metrics: pd.DataFrame, clubs: pd.DataFrame) -> pd.DataFrame:
    """Añade `dual`: el club juega 2 o más competiciones esa temporada."""
    n = clubs.groupby(["club_id", "temporada_id"])["competicion_id"].nunique().rename("n_comp").reset_index()
    out = metrics.merge(n, on=["club_id", "temporada_id"], how="left")
    out["dual"] = out["n_comp"].fillna(1) >= 2
    return out.drop(columns="n_comp")


def km_by_club(metrics: pd.DataFrame, names: dict[int, str], top: int = 20) -> pd.DataFrame:
    """Km de viaje acumulados por club y competición; solo los `top` clubes con más km."""
    grouped = metrics.groupby(["club_id", "competicion_id"], as_index=False)["km_trip"].sum()
    totals = grouped.groupby("club_id")["km_trip"].sum().nlargest(top)
    out = grouped[grouped["club_id"].isin(totals.index)].copy()
    out["Club"] = out["club_id"].map(names)
    order = {c: i for i, c in enumerate(totals.index)}
    out["orden"] = out["club_id"].map(order)
    return out.sort_values("orden").drop(columns=["club_id", "orden"]).rename(
        columns={"competicion_id": "Competición", "km_trip": "Km"}
    )


def venue_counts(metrics: pd.DataFrame, venues: pd.DataFrame) -> pd.DataFrame:
    """Partidos jugados por sede en el conjunto filtrado, con coordenadas."""
    one_per_game = metrics.drop_duplicates("partido_id")
    counts = one_per_game.groupby("sede_id").size().rename("partidos").reset_index()
    out = counts.merge(venues, left_on="sede_id", right_on="id")
    return out[["nombre", "pais", "lat", "lon", "partidos", "revisar"]]


def trip_lines(metrics: pd.DataFrame, venues: pd.DataFrame) -> pd.DataFrame:
    """Viajes de un club: sede base y sede de cada partido como visitante, con número de veces."""
    away = metrics[metrics["home"] == 0].dropna(subset=["base_sede_id", "sede_id"])
    trips = away.groupby(["base_sede_id", "sede_id"]).size().rename("veces").reset_index()
    coords = venues.set_index("id")[["nombre", "lat", "lon"]]
    base = coords.add_prefix("base_").loc[trips["base_sede_id"]].reset_index(drop=True)
    dest = coords.add_prefix("destino_").loc[trips["sede_id"]].reset_index(drop=True)
    return pd.concat([trips.reset_index(drop=True), base, dest], axis=1)


def travel_hours(km_round_trip: pd.Series) -> pd.Series:
    """Horas aproximadas de viaje (ida y vuelta): min(autobús, avión + aeropuerto) por trayecto. Es una estimación."""
    one_way = km_round_trip / 2
    return 2 * np.minimum(one_way / BUS_KMH, one_way / FLIGHT_KMH + AIRPORT_HOURS)


def add_result_columns(metrics: pd.DataFrame) -> pd.DataFrame:
    """Añade `win_pct` (victoria = 100, derrota = 0) y `trip_hours` para las gráficas de resultados."""
    out = metrics.copy()
    out["win_pct"] = out["win"] * 100
    out["trip_hours"] = travel_hours(out["km_trip"])
    return out


def _aggregate(data: pd.DataFrame, by: list[str], value: str) -> pd.DataFrame:
    """Media de `value` por grupos, con n y error estándar."""
    agg = data.groupby(by, observed=True)[value].agg(media="mean", n="size", sd="std").reset_index()
    agg["se"] = (agg["sd"] / np.sqrt(agg["n"])).fillna(0.0)
    return agg.drop(columns="sd")


def binned_effect(metrics: pd.DataFrame, column: str, value: str, group: str = "competicion_id") -> pd.DataFrame:
    """Media de `value` por tramo de `column` y grupo, con n y error estándar.

    `column` debe estar en BINS. Los tramos sin datos no aparecen.
    """
    bins, labels = BINS[column]
    data = metrics.dropna(subset=[column, value]).copy()
    data["tramo"] = pd.cut(data[column], bins=bins, labels=labels, right=True)
    return _aggregate(data, ["tramo", group], value)


def home_away_effect(metrics: pd.DataFrame, value: str = "win_pct") -> pd.DataFrame:
    """Media de `value` en casa y fuera por competición (columna `tramo` = Local o Visitante)."""
    data = metrics.dropna(subset=[value]).copy()
    data["tramo"] = pd.Categorical(data["home"].map({1: "Local", 0: "Visitante"}), categories=["Local", "Visitante"])
    return _aggregate(data, ["tramo", "competicion_id"], value)


def away_trip_effect(metrics: pd.DataFrame, unit: str, value: str) -> pd.DataFrame:
    """Resultado de los partidos fuera según el viaje; `unit` es "km_trip" o "trip_hours"."""
    return binned_effect(metrics[metrics["home"] == 0], unit, value)


def rest_trip_grid(metrics: pd.DataFrame, value: str, min_n: int = MIN_CELL) -> pd.DataFrame:
    """Media de `value` en partidos fuera por descanso (filas) y km de viaje (columnas); NaN si hay menos de `min_n`."""
    away = metrics[metrics["home"] == 0].dropna(subset=["rest_days", "km_trip", value]).copy()
    away["descanso"] = pd.cut(away["rest_days"], bins=REST_BINS, labels=REST_LABELS, right=True)
    away["viaje"] = pd.cut(away["km_trip"], bins=KM_TRIP_BINS, labels=KM_TRIP_LABELS, right=True)
    grid = away.groupby(["descanso", "viaje"], observed=False)[value].agg(media="mean", n="size").reset_index()
    grid.loc[grid["n"] < min_n, "media"] = np.nan
    return grid
