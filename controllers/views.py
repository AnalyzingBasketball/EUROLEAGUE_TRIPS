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


def add_flags(table: pd.DataFrame, codes: pd.Series, flags: dict[str, str] | None) -> pd.DataFrame:
    """Inserta la columna «Bandera» antes de «País», con la bandera del código de país de cada fila."""
    if not flags:
        return table
    # Como categoría, cada bandera viaja una sola vez al navegador (22 distintas) en lugar de una por fila.
    table.insert(table.columns.get_loc("País"), "Bandera", codes.map(flags).astype("category"))
    return table


def venues_table(venues: pd.DataFrame, flags: dict[str, str] | None = None) -> pd.DataFrame:
    """Catálogo de sedes con nombres de columna y país en español, listo para mostrar; con `flags`, añade la bandera."""
    out = pd.DataFrame({
        "Id": venues["id"], "Sede": venues["nombre"], "Ciudad": venues["ciudad"], "País": venues["pais"].map(country_name),
        "Latitud": venues["lat"], "Longitud": venues["lon"],
        "Precisión": venues["precision"].map(PRECISION_NAMES).fillna(venues["precision"]),
        "Revisar": venues["revisar"].map({0: "No", 1: "Sí"}),
    })
    return add_flags(out, venues["pais"], flags)


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


def add_crests(table: pd.DataFrame, crests: dict[str, str] | None) -> pd.DataFrame:
    """Inserta las columnas «Escudo» (antes de Club) y «Escudo rival» (antes de Rival) con la dirección de cada escudo."""
    if not crests:
        return table
    # Como categoría, cada escudo viaja una sola vez al navegador (78 distintos) en lugar de una por fila.
    table.insert(table.columns.get_loc("Club"), "Escudo", table["Club"].map(crests).astype("category"))
    table.insert(table.columns.get_loc("Rival"), "Escudo rival", table["Rival"].map(crests).astype("category"))
    return table


def trip_table(metrics: pd.DataFrame, names: dict[int, str], venues: pd.DataFrame,
               crests: dict[str, str] | None = None, flags: dict[str, str] | None = None) -> pd.DataFrame:
    """Calendario con descanso y km, listo para mostrar; con `crests` añade los escudos y con `flags` la bandera de la sede."""
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
    out = add_flags(out, metrics["sede_id"].map(sedes["pais"]), flags)
    return add_crests(out.sort_values(["Fecha", "Club"]).reset_index(drop=True), crests)


def fatigue_table(metrics: pd.DataFrame, names: dict[int, str], crests: dict[str, str] | None = None) -> pd.DataFrame:
    """Descanso, carga y rotación por partido, listo para mostrar; con `crests`, añade los escudos."""
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
    return add_crests(out.sort_values(["Fecha", "Club"]).reset_index(drop=True), crests)


def api_club_names(live: pd.DataFrame, side: str, aliases: pd.DataFrame) -> pd.Series:
    """Nombre canónico del club local (`side="local"`) o visitante (`"road"`) de cada partido de la API.

    La API escribe los nombres de otra forma que la base (Kosner Baskonia Vitoria-Gasteiz frente a Baskonia), así que se
    busca por código de club, competición y temporada en la tabla de alias.
    """
    def lookup(row: pd.Series) -> str | None:
        rows = aliases[(aliases["competicion_id"] == row["comp"]) & (aliases["codigo"] == row[f"{side}_code"])
                       & (aliases["temporada_desde"] <= row["season"])
                       & (aliases["temporada_hasta"].isna() | (aliases["temporada_hasta"] >= row["season"]))]
        return rows["club"].iloc[0] if len(rows) else None

    return live.apply(lookup, axis=1)


def upcoming_games(live: pd.DataFrame, limit: int = 20, crests: dict[str, str] | None = None,
                   aliases: pd.DataFrame | None = None) -> pd.DataFrame:
    """Próximos partidos sin jugar de la API, ordenados por fecha; con `crests` y `aliases`, añade los escudos."""
    pending = live[live["jugado"] == 0].sort_values(["fecha", "hora_utc"]).head(limit)
    out = pd.DataFrame({
        "Fecha": pending["fecha"],
        "Hora UTC": pending["hora_utc"].fillna("").str[11:16],
        "Jornada": pending["jornada"],
        "Local": pending["local_name"],
        "Visitante": pending["road_name"],
    }).reset_index(drop=True)
    if not crests or aliases is None or pending.empty:
        return out
    pending = pending.reset_index(drop=True)
    for column, side, label in (("Local", "local", "Escudo"), ("Visitante", "road", "Escudo visitante")):
        crest = api_club_names(pending, side, aliases).map(crests).astype("category")
        out.insert(out.columns.get_loc(column), label, crest)
    return out
