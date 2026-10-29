"""Figuras Plotly de la aplicación. Colores fijos por competición (la entidad, no su posición)."""
import pandas as pd
import plotly.graph_objects as go

from controllers.labels import country_name

COMP_NAMES = {"ACB": "ACB", "E": "Euroliga", "U": "EuroCup"}
COMP_ORDER = ["ACB", "E", "U"]

# Tres primeros colores categóricos validados para todas las parejas (azul, naranja, aguamarina), en claro y oscuro.
PALETTES = {
    False: {"ACB": "#2a78d6", "E": "#eb6834", "U": "#1baf7a", "ink": "#0b0b0b", "muted": "#52514e",
            "grid": "rgba(0,0,0,0.12)", "surface": "#ffffff", "land": "#ececea", "line": "#8a8985",
            "div_neg": "#a98bd0", "div_mid": "#ececea", "div_pos": "#f0b93a"},
    True: {"ACB": "#3987e5", "E": "#d95926", "U": "#199e70", "ink": "#f0efec", "muted": "#c3c2b7",
           "grid": "rgba(255,255,255,0.14)", "surface": "#0e1117", "land": "#262730", "line": "#8a8985",
           "div_neg": "#6d4a99", "div_mid": "#2d2f38", "div_pos": "#b88a1f"},
}


def _layout(fig: go.Figure, pal: dict, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": pal["ink"], "size": 13}, margin={"l": 10, "r": 10, "t": 30, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0, "title": None,
                "traceorder": "normal"},
    )
    axis = {"gridcolor": pal["grid"], "zerolinecolor": pal["grid"], "linecolor": pal["grid"], "automargin": True,
            "title_standoff": 12}
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def km_by_club_figure(data: pd.DataFrame, dark: bool) -> go.Figure:
    """Barras horizontales apiladas: km de viaje por club y competición."""
    pal = PALETTES[dark]
    fig = go.Figure()
    for comp in COMP_ORDER:
        part = data[data["Competición"] == comp]
        if part.empty:
            continue
        fig.add_bar(
            y=part["Club"], x=part["Km"], orientation="h", name=COMP_NAMES[comp],
            marker={"color": pal[comp], "line": {"color": pal["surface"], "width": 2}},
            hovertemplate="%{y}<br>" + COMP_NAMES[comp] + ": %{x:,.0f} km<extra></extra>",
        )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title="Km de viaje acumulados (ida y vuelta)", tickformat=",")
    height = max(320, 24 * data["Club"].nunique() + 90)
    return _layout(fig, pal, height)


def trip_map_figure(venues: pd.DataFrame, lines: pd.DataFrame | None, dark: bool) -> go.Figure:
    """Mapa: sedes (tamaño = partidos) y, si hay club elegido, líneas base-sede de cada viaje."""
    pal = PALETTES[dark]
    fig = go.Figure()
    if lines is not None and not lines.empty:
        for r in lines.itertuples():
            fig.add_trace(go.Scattergeo(
                lon=[r.base_lon, r.destino_lon], lat=[r.base_lat, r.destino_lat], mode="lines",
                line={"width": 1.5, "color": pal["E"]}, showlegend=False, hoverinfo="skip",
            ))
    fig.add_trace(go.Scattergeo(
        lon=venues["lon"], lat=venues["lat"], mode="markers", name="Sedes",
        marker={"size": (venues["partidos"] ** 0.5 * 5 + 5).clip(upper=26), "color": pal["ACB"], "opacity": 0.85,
                "line": {"color": pal["surface"], "width": 2}},
        text=venues["nombre"] + " (" + venues["pais"].map(country_name) + ")",
        customdata=venues["partidos"], hovertemplate="%{text}<br>%{customdata} partidos<extra></extra>",
        showlegend=False,
    ))
    fig.update_geos(
        projection_type="natural earth", showland=True, landcolor=pal["land"], showcountries=True,
        countrycolor=pal["grid"], showocean=False, showcoastlines=False, showframe=False,
        bgcolor="rgba(0,0,0,0)", fitbounds="locations",
    )
    return _layout(fig, pal, 480)


def effect_figure(data: pd.DataFrame, y_title: str, x_title: str, dark: bool) -> go.Figure:
    """Barras agrupadas por tramo y competición, con error estándar (±1,96 EE) y n en el tooltip."""
    pal = PALETTES[dark]
    fig = go.Figure()
    for comp in COMP_ORDER:
        part = data[data["competicion_id"] == comp]
        if part.empty:
            continue
        fig.add_bar(
            x=part["tramo"].astype(str), y=part["media"], name=COMP_NAMES[comp], customdata=part["n"],
            error_y={"type": "data", "array": 1.96 * part["se"], "thickness": 1.5, "color": pal["muted"]},
            marker={"color": pal[comp], "line": {"color": pal["surface"], "width": 2}},
            hovertemplate="%{x}<br>" + COMP_NAMES[comp] + ": %{y:.2f} (n=%{customdata})<extra></extra>",
        )
    fig.update_layout(barmode="group")
    fig.update_xaxes(title=x_title, showgrid=False, categoryorder="array", categoryarray=list(data["tramo"].astype(str).unique()))
    fig.update_yaxes(title=y_title)
    return _layout(fig, pal)


def rest_trip_heatmap(grid: pd.DataFrame, measure: str, center: float, dark: bool) -> go.Figure:
    """Mapa de calor descanso x viaje. Color divergente respecto a `center` (la media de los partidos fuera)."""
    pal = PALETTES[dark]
    z = grid.pivot(index="descanso", columns="viaje", values="media")
    n = grid.pivot(index="descanso", columns="viaje", values="n")
    text = z.map(lambda v: "" if pd.isna(v) else f"{round(v, 1) + 0.0:.1f}") + n.map(lambda k: f"<br>n={k}" if k else "")
    text = text.where(z.notna(), "")
    fig = go.Figure(go.Heatmap(
        x=[str(c) for c in z.columns], y=[str(r) for r in z.index], z=z.to_numpy(), text=text.to_numpy(),
        texttemplate="%{text}", customdata=n.to_numpy(), zmid=center, xgap=2, ygap=2,
        colorscale=[[0, pal["div_neg"]], [0.5, pal["div_mid"]], [1, pal["div_pos"]]],
        colorbar={"title": measure, "thickness": 12},
        hovertemplate="%{y}<br>%{x}<br>" + measure + ": %{z:.2f} (n=%{customdata})<extra></extra>",
    ))
    fig.update_xaxes(title="Km del viaje (ida y vuelta)", showgrid=False, side="bottom")
    fig.update_yaxes(title="Días de descanso", showgrid=False, autorange="reversed")
    return _layout(fig, pal, 380)
