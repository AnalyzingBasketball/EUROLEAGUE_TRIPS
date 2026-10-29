"""Versiones Matplotlib de las gráficas, para incrustarlas en el PDF (Plotly necesita kaleido y Chrome para exportar)."""
from io import BytesIO

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

from controllers.charts import COMP_NAMES, COMP_ORDER, PALETTES
from models.geo_model import load_country_rings

PAL = PALETTES[False]  # el PDF siempre sale sobre fondo blanco


def _png(fig: Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    return buf.getvalue()


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y" if ax.name == "rectilinear" else "both", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


def km_by_club_png(data: pd.DataFrame) -> bytes:
    """Barras horizontales apiladas de km por club y competición."""
    clubs = list(dict.fromkeys(data["Club"]))
    fig = Figure(figsize=(8, max(3.0, 0.28 * len(clubs) + 1.2)))
    ax = fig.subplots()
    left = pd.Series(0.0, index=clubs)
    for comp in COMP_ORDER:
        part = data[data["Competición"] == comp].set_index("Club")["Km"].reindex(clubs).fillna(0.0)
        if part.sum() == 0:
            continue
        ax.barh(clubs, part, left=left, color=PAL[comp], edgecolor="white", linewidth=1.2, label=COMP_NAMES[comp])
        left = left + part
    ax.invert_yaxis()
    ax.set_xlabel("Km de viaje acumulados (ida y vuelta)")
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}".replace(",", "."))
    ax.legend(frameon=False, ncol=3, loc="lower right")
    _style(ax)
    ax.grid(axis="y", visible=False)
    return _png(fig)


def effect_png(data: pd.DataFrame, y_title: str, x_title: str) -> bytes:
    """Barras agrupadas por tramo y competición con ±1,96 errores estándar."""
    labels = list(dict.fromkeys(data["tramo"].astype(str)))
    comps = [c for c in COMP_ORDER if (data["competicion_id"] == c).any()]
    width = 0.8 / max(len(comps), 1)
    fig = Figure(figsize=(8, 3.8))
    ax = fig.subplots()
    for i, comp in enumerate(comps):
        part = data[data["competicion_id"] == comp].assign(tramo=lambda d: d["tramo"].astype(str)).set_index("tramo")
        part = part.reindex(labels)
        xs = [j + (i - (len(comps) - 1) / 2) * width for j in range(len(labels))]
        ax.bar(xs, part["media"].fillna(0.0), width=width * 0.92, color=PAL[comp], edgecolor="white", linewidth=1.2,
               label=COMP_NAMES[comp], yerr=1.96 * part["se"].fillna(0.0), ecolor="#52514e", capsize=2)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xticks(range(len(labels)), labels, fontsize=8)
    ax.set_xlabel(x_title)
    ax.set_ylabel(y_title)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    _style(ax)
    ax.grid(axis="x", visible=False)
    return _png(fig)


def venue_map_png(venues: pd.DataFrame, lines: pd.DataFrame | None) -> bytes:
    """Sedes (tamaño = partidos) y viajes del club sobre los contornos de los países."""
    fig = Figure(figsize=(8, 4.8))
    ax = fig.subplots()
    for ring in load_country_rings():
        ax.add_patch(Polygon(ring, closed=True, facecolor="#ececea", edgecolor="white", linewidth=0.6, zorder=0))
    if lines is not None:
        for r in lines.itertuples():
            ax.plot([r.base_lon, r.destino_lon], [r.base_lat, r.destino_lat], color=PAL["E"], linewidth=1, alpha=0.8)
    ax.scatter(venues["lon"], venues["lat"], s=venues["partidos"].clip(upper=60) * 4 + 12, color=PAL["ACB"],
               alpha=0.8, edgecolor="white", linewidth=1.2)
    lons = pd.concat([venues["lon"], lines[["base_lon", "destino_lon"]].stack()]) if lines is not None else venues["lon"]
    lats = pd.concat([venues["lat"], lines[["base_lat", "destino_lat"]].stack()]) if lines is not None else venues["lat"]
    ax.set_xlim(lons.min() - 4, lons.max() + 4)
    ax.set_ylim(lats.min() - 3, lats.max() + 3)
    ax.set_aspect(1 / np.cos(np.radians(lats.mean())))  # a latitudes altas los grados de longitud miden menos
    ax.set_axis_off()
    return _png(fig)


def rest_trip_heatmap_png(grid: pd.DataFrame, measure: str, center: float) -> bytes:
    """Mapa de calor descanso x viaje con n en cada celda; las celdas con pocos partidos quedan en blanco."""
    z = grid.pivot(index="descanso", columns="viaje", values="media")
    n = grid.pivot(index="descanso", columns="viaje", values="n")
    values = z.to_numpy(dtype=float)
    span = max(np.nanmax(np.abs(values - center)), 1e-6) if np.isfinite(values).any() else 1.0
    cmap = LinearSegmentedColormap.from_list("div", [PAL["div_neg"], PAL["div_mid"], PAL["div_pos"]])
    fig = Figure(figsize=(8, 3.6))
    ax = fig.subplots()
    image = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, norm=TwoSlopeNorm(center, center - span, center + span),
                      aspect="auto")
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if np.isfinite(values[i, j]):
                ax.text(j, i, f"{round(values[i, j], 1) + 0.0:.1f}\nn={int(n.iat[i, j])}", ha="center", va="center", fontsize=8, color="#0b0b0b")
    ax.set_xticks(range(values.shape[1]), [str(c) for c in z.columns], fontsize=8)
    ax.set_yticks(range(values.shape[0]), [str(r) for r in z.index], fontsize=8)
    ax.set_xlabel("Km del viaje (ida y vuelta)")
    ax.set_ylabel("Días de descanso")
    fig.colorbar(image, ax=ax, label=measure, fraction=0.04, pad=0.02).outline.set_visible(False)
    for side in ax.spines.values():
        side.set_visible(False)
    return _png(fig)
