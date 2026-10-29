import requests
import streamlit as st

from common.menu import iniciar_pagina
from common.print_tools import print_button
from common.theme import is_dark
from controllers.chart_data import binned_effect, default_season
from controllers.charts import effect_figure
from controllers.reports import fatigue_report
from controllers.views import (
    club_names,
    fatigue_table,
    filter_metrics,
    seasons_label,
    upcoming_games,
)
from models.api_model import get_live_games
from models.sqlite_model import get_clubs, get_metrics

ROTATION = {
    "players_10": "Jugadores con 10 minutos o más",
    "top5_share": "Cuota de minutos de los 5 que más juegan",
    "starters_changed": "Titulares cambiados respecto al partido anterior",
}

if iniciar_pagina("Fatiga y rotaciones", "🏀"):
    st.title("Fatiga y rotaciones")
    actions = st.container()
    metrics, clubs = get_metrics(), get_clubs()
    names = club_names(clubs)

    c1, c2, c3 = st.columns(3)
    seasons = sorted(metrics["temporada_id"].unique(), reverse=True)
    season = c1.selectbox("Temporada", seasons, index=seasons.index(default_season(metrics)),
                          format_func=seasons_label, key="season_f")
    comps = c2.multiselect("Competición", ["ACB", "E"], default=["ACB", "E"],
                           format_func={"ACB": "ACB", "E": "Euroliga"}.get, key="comps_f")
    only_dual = c3.checkbox("Solo clubes con doble competición", value=True, key="dual_f")
    scope = filter_metrics(metrics, season, comps)
    if only_dual:
        scope = scope[scope["dual"]]

    st.subheader("Fuente 1 · SQLite: descanso, carga y rotación por partido")
    st.caption("La rotación solo existe en ACB y Euroliga: no hay minutos de EuroCup.")
    st.dataframe(fatigue_table(scope, names), width="stretch", hide_index=True, height=320)

    current = int(seasons[0])
    st.subheader("Fuente 2 · API de Euroliga: próximos partidos")
    st.caption(f"Temporada en curso: {seasons_label(current)}.")
    api_comp = st.radio("Competición de la API", ["E", "U"], horizontal=True,
                        format_func={"E": "Euroliga", "U": "EuroCup"}.get, key="api_comp")
    try:
        live = get_live_games(api_comp, current)
        if live.empty:
            st.info("La API no devuelve partidos para esta temporada.")
        else:
            upcoming = upcoming_games(live)
            if upcoming.empty:
                st.info("No quedan partidos por jugar en la temporada en curso.")
            else:
                st.dataframe(upcoming, width="stretch", hide_index=True, height=260)
    except (requests.RequestException, ValueError, KeyError) as exc:  # la app no debe romperse si la API falla
        st.error(f"No se pudo consultar la API de Euroliga: {exc}")

    st.subheader("Gráficos")
    st.caption("Barras: media por tramo con ±1,96 errores estándar. Mide correlación, no causa. Todas las temporadas de la selección de competición.")
    all_seasons = metrics[metrics["competicion_id"].isin(comps)]
    if only_dual:
        all_seasons = all_seasons[all_seasons["dual"]]
    dark = is_dark()
    if all_seasons.empty:
        st.info("No hay partidos con estos filtros.")
    else:
        st.markdown("**Rendimiento según el descanso**")
        rest = binned_effect(all_seasons, "rest_days", "margin_resid")
        st.plotly_chart(effect_figure(rest, "Margen ajustado medio (puntos)", "Días desde el partido anterior", dark),
                        theme=None, width="stretch")
        with st.expander("Ver los datos del gráfico"):
            st.dataframe(rest.round(2), width="stretch", hide_index=True)

        rot_key = st.selectbox("Medida de rotación", list(ROTATION), format_func=ROTATION.get, key="rot")
        st.markdown(f"**{ROTATION[rot_key]} según los km de los últimos 7 días**")
        rot = binned_effect(all_seasons, "km_7d", rot_key)
        st.plotly_chart(effect_figure(rot, ROTATION[rot_key], "Km de viaje acumulados en 7 días", dark),
                        theme=None, width="stretch")
        with st.expander("Ver los datos del gráfico"):
            st.dataframe(rot.round(3), width="stretch", hide_index=True)

    user = st.session_state["usuario"]  # el PDF se genera al pulsar, fuera del hilo del script: no puede leer la sesión
    with actions:
        b1, b2, _ = st.columns([3, 3, 4], vertical_alignment="center")
        with b1:
            print_button()
        rot_now = st.session_state.get("rot", "players_10")
        report_filters = {"Temporada de la tabla": seasons_label(season), "Competiciones": ", ".join(comps),
                          "Solo doble competición": "sí" if only_dual else "no"}
        b2.download_button(
            "📄 Exportar a PDF",
            data=lambda: fatigue_report(user, report_filters, fatigue_table(scope, names),
                                        all_seasons, rot_now, ROTATION[rot_now]),
            file_name=f"fatiga_rotaciones_{season}.pdf", mime="application/pdf", width="stretch", disabled=all_seasons.empty,
        )
