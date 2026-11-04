"""Datos del mapa interactivo: sedes por competición, rutas de viaje, acumulado por meses y partidos de una sede."""
import pandas as pd

from controllers.charts import COMP_NAMES
from controllers.ingest import haversine_km
from controllers.views import add_crests

TOP_ROUTES = 25  # sin club elegido, el mapa dibuja solo las rutas más repetidas para no taparse
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]
ROUTE_COLUMNS = ["competicion_id", "veces", "km", "origen_nombre", "origen_lat", "origen_lon",
                 "destino_nombre", "destino_lat", "destino_lon"]


def venue_stats(metrics: pd.DataFrame, venues: pd.DataFrame, names: dict[int, str]) -> pd.DataFrame:
    """Partidos por sede y competición, con coordenadas, total de la sede y clubes que juegan en casa allí."""
    games = metrics.drop_duplicates("partido_id")
    counts = games.groupby(["sede_id", "competicion_id"]).size().rename("partidos").reset_index()
    counts["total"] = counts.groupby("sede_id")["partidos"].transform("sum")
    clubs = (metrics[metrics["home"] == 1].groupby("sede_id")["club_id"]
             .apply(lambda ids: ", ".join(sorted({names[i] for i in ids}))).rename("clubes"))
    out = counts.merge(venues[["id", "nombre", "ciudad", "pais", "lat", "lon"]], left_on="sede_id", right_on="id")
    out = out.drop(columns="id").merge(clubs, left_on="sede_id", right_index=True, how="left")
    return out.fillna({"clubes": ""})


def route_lines(metrics: pd.DataFrame, venues: pd.DataFrame, top: int | None = None) -> pd.DataFrame:
    """Viajes como visitante de la sede base a la del partido, por competición, con número de veces y km (ida y vuelta)."""
    away = metrics[metrics["home"] == 0].dropna(subset=["base_sede_id", "sede_id"])
    if away.empty:
        return pd.DataFrame(columns=ROUTE_COLUMNS)
    trips = away.groupby(["base_sede_id", "sede_id", "competicion_id"]).size().rename("veces").reset_index()
    coords = venues.set_index("id")[["nombre", "lat", "lon"]]
    origin = coords.add_prefix("origen_").loc[trips["base_sede_id"]].reset_index(drop=True)
    target = coords.add_prefix("destino_").loc[trips["sede_id"]].reset_index(drop=True)
    out = pd.concat([trips.reset_index(drop=True), origin, target], axis=1)
    out["km"] = [2 * haversine_km(r.origen_lat, r.origen_lon, r.destino_lat, r.destino_lon) for r in out.itertuples()]
    out = out[out["km"] > 0].sort_values(["veces", "km"], ascending=False)
    return (out.head(top) if top else out)[ROUTE_COLUMNS].reset_index(drop=True)


def month_label(period: pd.Period) -> str:
    """Periodo mensual -> «octubre 2025»."""
    return f"{MONTHS[period.month - 1]} {period.year}"


def month_frames(metrics: pd.DataFrame, venues: pd.DataFrame, names: dict[int, str],
                 with_routes: bool) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Un cuadro por mes con lo acumulado hasta el final de ese mes: (etiqueta, sedes, rutas).

    Las rutas solo se calculan con un club elegido: con todos los clubes se taparían entre sí.
    """
    months = metrics["fecha"].dt.to_period("M")
    frames = []
    for month in sorted(months.unique()):
        upto = metrics[months <= month]
        routes = route_lines(upto, venues) if with_routes else pd.DataFrame(columns=ROUTE_COLUMNS)
        frames.append((month_label(month), venue_stats(upto, venues, names), routes))
    return frames


def venue_options(stats: pd.DataFrame) -> dict[int, str]:
    """Sedes con partidos en el mapa, de la que más a la que menos, como {id: «Sede (Ciudad)»} para elegir una."""
    ranked = stats.groupby(["sede_id", "nombre", "ciudad"], dropna=False)["partidos"].sum().reset_index()
    ranked = ranked.sort_values(["partidos", "nombre"], ascending=[False, True])
    return {int(r.sede_id): f"{r.nombre} ({r.ciudad}) · {r.partidos} partidos" for r in ranked.itertuples()}


def venue_games(metrics: pd.DataFrame, venue_id: int, names: dict[int, str],
                crests: dict[str, str] | None = None) -> pd.DataFrame:
    """Partidos jugados en una sede, uno por partido, con local, visitante y resultado."""
    here = metrics[metrics["sede_id"] == venue_id].sort_values("home", ascending=False).drop_duplicates("partido_id")
    is_home = here["home"] == 1  # con un club elegido, un partido fuera aparece desde su punto de vista: se da la vuelta
    local_id = here["club_id"].where(is_home, here["rival_id"])
    away_id = here["rival_id"].where(is_home, here["club_id"])
    pts_local = here["pts_for"].where(is_home, here["pts_against"]).astype(int)
    pts_away = here["pts_against"].where(is_home, here["pts_for"]).astype(int)
    out = pd.DataFrame({
        "Fecha": here["fecha"].dt.date,
        "Competición": here["competicion_id"].map(COMP_NAMES),
        "Club": local_id.map(names),
        "Rival": away_id.map(names),
        "Resultado": pts_local.astype(str) + "-" + pts_away.astype(str),
    }).sort_values("Fecha").reset_index(drop=True)
    out = add_crests(out, crests)
    return out.rename(columns={"Club": "Local", "Rival": "Visitante", "Escudo rival": "Escudo visitante"})
