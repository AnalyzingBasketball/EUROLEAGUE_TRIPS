"""Datos agregados para los gráficos. Funciones puras: DataFrame entra, DataFrame sale."""
import numpy as np
import pandas as pd

REST_BINS = [0, 2, 3, 5, 7, np.inf]
REST_LABELS = ["2 días o menos", "3 días", "4-5 días", "6-7 días", "8 días o más"]
KM_BINS = [-1, 0, 1000, 3000, np.inf]
KM_LABELS = ["Sin viaje (0 km)", "1-1.000 km", "1.000-3.000 km", "Más de 3.000 km"]

BINS = {
    "rest_days": (REST_BINS, REST_LABELS),
    "km_7d": (KM_BINS, KM_LABELS),
}


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


def binned_effect(metrics: pd.DataFrame, column: str, value: str, group: str = "competicion_id") -> pd.DataFrame:
    """Media de `value` por tramo de `column` y grupo, con n y error estándar.

    `column` debe estar en BINS ("rest_days" o "km_7d"). Los tramos sin datos no aparecen.
    """
    bins, labels = BINS[column]
    data = metrics.dropna(subset=[column, value]).copy()
    data["tramo"] = pd.cut(data[column], bins=bins, labels=labels, right=True)
    agg = data.groupby(["tramo", group], observed=True)[value].agg(media="mean", n="size", sd="std").reset_index()
    agg["se"] = (agg["sd"] / np.sqrt(agg["n"])).fillna(0.0)
    return agg.drop(columns="sd")
