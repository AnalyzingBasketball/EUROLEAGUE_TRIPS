"""Mapa interactivo con fondo de calles (Plotly Scattermap): sedes por competición, rutas y animación por meses."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from controllers.charts import COMP_NAMES, COMP_ORDER, PALETTES
from controllers.labels import country_name

STYLES = {False: "carto-positron", True: "carto-darkmatter"}  # teselas gratuitas de Carto, sin clave
HEIGHT = 540


def _marker_size(games: pd.Series) -> pd.Series:
    """Diámetro en píxeles: crece con la raíz del número de partidos y se acota."""
    return (8 + 3.2 * np.sqrt(games)).clip(upper=34)


def _view(lat: pd.Series, lon: pd.Series) -> tuple[dict, float]:
    """Centro y zoom que encuadran todos los puntos (aproximado para un mapa de unos 900 x 540 píxeles)."""
    if lat.empty:
        return {"lat": 45.0, "lon": 12.0}, 3.0
    center = {"lat": float((lat.max() + lat.min()) / 2), "lon": float((lon.max() + lon.min()) / 2)}
    lon_span = max(float(lon.max() - lon.min()), 1.0) * 1.3
    lat_span = max(float(lat.max() - lat.min()), 1.0) * 1.3
    zoom_lon = np.log2(640 / lon_span)
    zoom_lat = np.log2(340 * np.cos(np.radians(center["lat"])) / lat_span)
    return center, float(np.clip(min(zoom_lon, zoom_lat), 2.0, 9.0))


def _hover_text(stats: pd.DataFrame) -> pd.Series:
    """Texto emergente de cada sede: lugar, partidos de la competición, total y clubes locales."""
    comp = stats["competicion_id"].map(COMP_NAMES)
    place = "<b>" + stats["nombre"] + "</b><br>" + stats["ciudad"].fillna("") + ", " + stats["pais"].map(country_name)
    games = comp + ": " + stats["partidos"].astype(str) + " partidos"
    total = np.where(stats["total"] > stats["partidos"], "<br>Total en la sede: " + stats["total"].astype(str), "")
    clubs = np.where(stats["clubes"] != "", "<br>Clubes: " + stats["clubes"], "")
    return place + "<br>" + games + total + clubs


def _venue_trace(stats: pd.DataFrame, comp: str, pal: dict, show_legend: bool = True) -> go.Scattermap:
    part = stats[stats["competicion_id"] == comp]
    empty = part.empty  # un punto vacío mantiene la competición en la leyenda aunque aún no tenga partidos
    return go.Scattermap(
        lat=[None] if empty else part["lat"], lon=[None] if empty else part["lon"], mode="markers",
        name=COMP_NAMES[comp], legendgroup=comp,
        showlegend=show_legend, marker={"size": 10 if empty else _marker_size(part["partidos"]), "color": pal[comp], "opacity": 0.8},
        customdata=part[["sede_id"]].to_numpy(), text=_hover_text(part) if len(part) else [],
        hovertemplate="%{text}<extra></extra>",
    )


def _route_traces(routes: pd.DataFrame, pal: dict) -> list[go.Scattermap]:
    """Una línea por ruta, más gruesa cuanto más veces se repite, y un punto en su mitad con los datos del viaje."""
    traces = []
    mid_lat, mid_lon, mid_text, mid_color = [], [], [], []
    for r in routes.itertuples():
        traces.append(go.Scattermap(
            lat=[r.origen_lat, r.destino_lat], lon=[r.origen_lon, r.destino_lon], mode="lines", hoverinfo="skip",
            line={"width": 1.5 + min(r.veces, 8) * 0.7, "color": pal[r.competicion_id]}, opacity=0.55,
            showlegend=False,
        ))
        mid_lat.append((r.origen_lat + r.destino_lat) / 2)
        mid_lon.append((r.origen_lon + r.destino_lon) / 2)
        mid_color.append(pal[r.competicion_id])
        mid_text.append(f"<b>{r.origen_nombre} → {r.destino_nombre}</b><br>{COMP_NAMES[r.competicion_id]}: "
                        f"{r.veces} viajes<br>{r.km:,.0f} km ida y vuelta".replace(",", "."))
    if mid_lat:
        traces.append(go.Scattermap(
            lat=mid_lat, lon=mid_lon, mode="markers", marker={"size": 7, "color": mid_color, "opacity": 0.9},
            text=mid_text, hovertemplate="%{text}<extra></extra>", showlegend=False,
        ))
    return traces


def _base_layout(fig: go.Figure, dark: bool, lat: pd.Series, lon: pd.Series) -> go.Figure:
    pal = PALETTES[dark]
    center, zoom = _view(lat, lon)
    fig.update_layout(
        height=HEIGHT, paper_bgcolor="rgba(0,0,0,0)", font={"color": pal["ink"], "size": 13},
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "left", "x": 0, "title": None,
                "bgcolor": "rgba(0,0,0,0)"},
        map={"style": STYLES[dark], "center": center, "zoom": zoom},
    )
    return fig


def _highlight_trace(stats: pd.DataFrame, venue_id: int, pal: dict) -> go.Scattermap:
    """Círculo grande y translúcido bajo la sede elegida."""
    part = stats[stats["sede_id"] == venue_id]
    size = float(_marker_size(part["total"]).max()) + 16 if len(part) else 0
    return go.Scattermap(lat=part["lat"].head(1), lon=part["lon"].head(1), mode="markers", hoverinfo="skip",
                         marker={"size": size, "color": pal["ink"], "opacity": 0.3}, showlegend=False)


def detail_map_figure(stats: pd.DataFrame, routes: pd.DataFrame, dark: bool, highlight: int | None = None) -> go.Figure:
    """Mapa con calles: sedes por competición (la leyenda las enciende y apaga), rutas de viaje y, si se elige, una sede resaltada."""
    pal = PALETTES[dark]
    fig = go.Figure()
    for trace in _route_traces(routes, pal):
        fig.add_trace(trace)
    if highlight is not None:
        fig.add_trace(_highlight_trace(stats, highlight, pal))
    for comp in COMP_ORDER:  # las sedes van encima de las rutas para poder pulsarlas
        if (stats["competicion_id"] == comp).any():
            fig.add_trace(_venue_trace(stats, comp, pal))
    return _base_layout(fig, dark, stats["lat"], stats["lon"])


def _frame_traces(stats: pd.DataFrame, routes: pd.DataFrame, pal: dict) -> list[go.Scattermap]:
    """Seis trazas fijas por cuadro: sedes de cada competición y rutas de cada competición."""
    traces = [_venue_trace(stats, comp, pal) for comp in COMP_ORDER]
    for comp in COMP_ORDER:
        part = routes[routes["competicion_id"] == comp]
        lat, lon = [], []
        for r in part.itertuples():
            lat += [r.origen_lat, r.destino_lat, None]
            lon += [r.origen_lon, r.destino_lon, None]
        traces.append(go.Scattermap(lat=lat, lon=lon, mode="lines", line={"width": 2.5, "color": pal[comp]},
                                    opacity=0.55, hoverinfo="skip", showlegend=False))
    return traces


def animated_map_figure(frames: list[tuple[str, pd.DataFrame, pd.DataFrame]], dark: bool) -> go.Figure:
    """Mapa animado: un cuadro por mes con las sedes y los viajes acumulados hasta entonces."""
    pal = PALETTES[dark]
    _, stats, routes = frames[0]
    fig = go.Figure(data=_frame_traces(stats, routes, pal))
    fig.frames = [go.Frame(name=name, data=_frame_traces(s, r, pal), traces=list(range(6))) for name, s, r in frames]
    everything = pd.concat([f[1] for f in frames]) if frames else pd.DataFrame({"lat": [], "lon": []})
    _base_layout(fig, dark, everything["lat"], everything["lon"])
    play = {"frame": {"duration": 1100, "redraw": True}, "transition": {"duration": 0}, "fromcurrent": True}
    fig.update_layout(
        margin={"l": 24, "r": 24, "t": 30, "b": 110},
        updatemenus=[{
            "type": "buttons", "direction": "left", "x": 0.0, "y": 0.0, "xanchor": "left", "yanchor": "top",
            "pad": {"t": 8, "l": 4}, "bgcolor": pal["surface"], "bordercolor": pal["grid"],
            "buttons": [
                {"label": "Reproducir", "method": "animate", "args": [None, play]},
                {"label": "Pausa", "method": "animate",
                 "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]},
            ],
        }],
        sliders=[{
            "x": 0.0, "len": 1.0, "pad": {"t": 64, "b": 0, "l": 4, "r": 4}, "font": {"size": 11},
            "currentvalue": {"prefix": "Acumulado hasta: ", "font": {"size": 13}, "xanchor": "left"},
            "steps": [{"label": name[:3] + " " + name[-4:], "method": "animate",
                       "args": [[name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]}
                      for name, _, _ in frames],
        }],
    )
    return fig
