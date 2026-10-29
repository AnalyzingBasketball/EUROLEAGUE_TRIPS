"""Métricas de calendario, viaje y rotaciones por club y partido.

Todas las funciones son puras (DataFrame entra, DataFrame sale) y no dependen de Streamlit ni de SQLite.
Un partido jugado genera dos filas, una por club ("formato largo").
"""
import numpy as np
import pandas as pd

from controllers.ingest import haversine_km

WINDOWS = (7, 14)
HOME_ADVANTAGE_RIDGE = 1.0  # regularización de la fuerza de cada club en el ajuste del margen


def build_club_games(games: pd.DataFrame, sedes: pd.DataFrame) -> pd.DataFrame:
    """Pasa los partidos jugados a una fila por club, con resultado y coordenadas de la sede."""
    played = games[games["jugado"] == 1]
    coords = sedes.set_index("id")[["lat", "lon"]]
    out = []
    for side, other, own_pts, opp_pts, home in (
        ("local_id", "visitante_id", "pts_local", "pts_visitante", 1),
        ("visitante_id", "local_id", "pts_visitante", "pts_local", 0),
    ):
        part = pd.DataFrame({
            "partido_id": played["id"], "competicion_id": played["competicion_id"],
            "temporada_id": played["temporada_id"], "fecha": pd.to_datetime(played["fecha"]),
            "hora_utc": played["hora_utc"], "club_id": played[side], "rival_id": played[other],
            "home": home, "sede_id": played["sede_id"],
            "pts_for": played[own_pts].astype(float), "pts_against": played[opp_pts].astype(float),
        })
        out.append(part)
    cg = pd.concat(out, ignore_index=True)
    cg["margin"] = cg["pts_for"] - cg["pts_against"]
    cg["win"] = np.sign(cg["margin"]).map({1.0: 1.0, 0.0: 0.5, -1.0: 0.0})
    cg = cg.join(coords, on="sede_id")
    return sort_club_games(cg)


def sort_club_games(cg: pd.DataFrame) -> pd.DataFrame:
    """Orden cronológico por club (fecha y hora UTC si la hay)."""
    return cg.sort_values(["club_id", "fecha", "hora_utc", "partido_id"], na_position="last").reset_index(drop=True)


def _base_venue(cg: pd.DataFrame, sedes: pd.DataFrame) -> pd.Series:
    """Sede base de cada (club, temporada): la más usada como local; si no hay, la de todas las temporadas."""
    home = cg[cg["home"] == 1]
    by_season = home.groupby(["club_id", "temporada_id"])["sede_id"].agg(lambda s: s.mode().iloc[0])
    by_club = home.groupby("club_id")["sede_id"].agg(lambda s: s.mode().iloc[0])
    keys = list(zip(cg["club_id"], cg["temporada_id"]))
    return pd.Series(
        [by_season.get(k, by_club.get(k[0], np.nan)) for k in keys], index=cg.index, name="base_sede_id"
    )


def _rolling_sum_by_day(days: np.ndarray, values: np.ndarray, window: int) -> np.ndarray:
    """Suma de `values` de las filas con día en (d - window, d], incluida la propia fila."""
    cumulative = np.concatenate([[0.0], np.nancumsum(values)])
    start = np.searchsorted(days, days - window, side="right")
    return cumulative[np.arange(len(days)) + 1] - cumulative[start]


def add_rest_and_travel(cg: pd.DataFrame, sedes: pd.DataFrame) -> pd.DataFrame:
    """Añade descanso, km de viaje (ida y vuelta desde la base) y acumulados en 7 y 14 días.

    - rest_days: días desde el partido anterior del club en la misma temporada (cualquier competición).
    - km_trip: 0 en casa; ida y vuelta base-sede fuera.
    - km_prev: distancia desde la sede del partido anterior (cota superior si el club no vuelve a casa).
    - km_Nd: km_trip acumulado en los N días que terminan en el partido, incluido éste.
    - games_prev_7d: partidos en los 7 días anteriores (sin contar éste).
    """
    cg = sort_club_games(cg)
    coords = sedes.set_index("id")[["lat", "lon"]]
    base = _base_venue(cg, sedes)
    base_xy = coords.reindex(base.to_numpy()).set_axis(cg.index)
    one_way = np.array([
        haversine_km(a, b, c, d) if not np.isnan([a, b, c, d]).any() else np.nan
        for a, b, c, d in zip(base_xy["lat"], base_xy["lon"], cg["lat"], cg["lon"])
    ])
    cg["base_sede_id"] = base
    cg["km_trip"] = np.where(cg["home"] == 1, 0.0, 2 * one_way)

    for col in ("rest_days", "km_prev", "games_prev_7d", *(f"km_{w}d" for w in WINDOWS)):
        cg[col] = np.nan
    for idx in cg.groupby(["club_id", "temporada_id"]).groups.values():
        g = cg.loc[idx]
        days = ((g["fecha"] - pd.Timestamp("2000-01-01")).dt.days).to_numpy()
        cg.loc[idx, "rest_days"] = np.r_[np.nan, np.diff(days)]
        lat, lon = g["lat"].to_numpy(), g["lon"].to_numpy()
        cg.loc[idx, "km_prev"] = np.r_[np.nan, [
            haversine_km(lat[i - 1], lon[i - 1], lat[i], lon[i]) for i in range(1, len(g))
        ]]
        for w in WINDOWS:
            cg.loc[idx, f"km_{w}d"] = _rolling_sum_by_day(days, g["km_trip"].to_numpy(), w)
        before = np.searchsorted(days, days - 7, side="left")
        cg.loc[idx, "games_prev_7d"] = np.arange(len(days)) - before
    return cg


def add_rotation(cg: pd.DataFrame, minutes: pd.DataFrame) -> pd.DataFrame:
    """Añade métricas de rotación a partir de los minutos por jugador.

    - players_used / players_10: jugadores con minutos / con al menos 10 minutos.
    - top5_share: fracción de los minutos del equipo que juegan los 5 con más minutos.
    - hhi: concentración de minutos (suma de cuadrados de cada cuota); más alto = menos rotación.
    - starters_changed: titulares que no eran titulares en el partido anterior del club (misma temporada).
    """
    cg = sort_club_games(cg)
    m = minutes[minutes["minutos"] > 0]
    stats = []
    for (pid, club), g in m.groupby(["partido_id", "club_id"]):
        mins = g["minutos"].sort_values(ascending=False).to_numpy()
        share = mins / mins.sum()
        stats.append({
            "partido_id": pid, "club_id": club, "players_used": len(mins), "players_10": int((mins >= 10).sum()),
            "top5_share": share[:5].sum(), "hhi": float((share ** 2).sum()),
            "starters": frozenset(g.loc[g["titular"] == 1, "jugador"]),
        })
    cols = ["partido_id", "club_id", "players_used", "players_10", "top5_share", "hhi", "starters"]
    stats = pd.DataFrame(stats, columns=cols)
    cg = cg.merge(stats, on=["partido_id", "club_id"], how="left")
    cg = sort_club_games(cg)
    cg["starters_changed"] = np.nan
    for idx in cg.groupby(["club_id", "temporada_id"]).groups.values():
        prev = None
        for i in idx:
            cur = cg.at[i, "starters"]
            if isinstance(cur, frozenset):
                if prev is not None:
                    cg.at[i, "starters_changed"] = len(cur - prev)
                prev = cur
    return cg.drop(columns="starters")


def add_adjusted_margin(cg: pd.DataFrame) -> pd.DataFrame:
    """Añade margin_resid: margen real menos el esperado por fuerza de ambos clubes y ventaja de campo.

    El ajuste es una regresión de margen por competición y temporada (un coeficiente por club más la
    ventaja de campo, con regularización ridge en los clubes). Es un ajuste dentro de la muestra:
    mide rendimiento respecto al nivel medio del club esa temporada, no pronóstico previo al partido.
    """
    cg = cg.copy()
    cg["margin_resid"] = np.nan
    for _, part in cg.groupby(["competicion_id", "temporada_id"]):
        home = part[part["home"] == 1].set_index("partido_id")
        away = part[part["home"] == 0].set_index("partido_id")
        pids = home.index.intersection(away.index)
        if len(pids) == 0:
            continue
        h, a = home.loc[pids], away.loc[pids]
        clubs = sorted(set(h["club_id"]) | set(a["club_id"]))
        pos = {c: i for i, c in enumerate(clubs)}
        x = np.zeros((len(pids), len(clubs) + 1))
        x[np.arange(len(pids)), [pos[c] for c in h["club_id"]]] = 1
        x[np.arange(len(pids)), [pos[c] for c in a["club_id"]]] = -1
        x[:, -1] = 1  # ventaja de campo
        y = h["margin"].to_numpy()
        penalty = np.eye(x.shape[1]) * HOME_ADVANTAGE_RIDGE
        penalty[-1, -1] = 0
        beta = np.linalg.solve(x.T @ x + penalty, x.T @ y)
        resid = pd.Series(y - x @ beta, index=pids)
        mask = cg["competicion_id"].eq(part["competicion_id"].iloc[0]) & cg["temporada_id"].eq(part["temporada_id"].iloc[0])
        sign = np.where(cg.loc[mask, "home"] == 1, 1.0, -1.0)
        cg.loc[mask, "margin_resid"] = resid.reindex(cg.loc[mask, "partido_id"]).to_numpy() * sign
    return cg


def build_metrics(games: pd.DataFrame, sedes: pd.DataFrame, minutes: pd.DataFrame) -> pd.DataFrame:
    """Tabla final de métricas por club y partido jugado."""
    cg = build_club_games(games, sedes)
    cg = add_rest_and_travel(cg, sedes)
    cg = add_rotation(cg, minutes)
    return add_adjusted_margin(cg)
