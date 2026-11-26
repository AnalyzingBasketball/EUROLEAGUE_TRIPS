import requests
import streamlit as st

from common.menu import image_columns, iniciar_pagina
from common.print_tools import print_button, print_table
from common.theme import is_dark
from controllers.chart_data import (
    RESULT_MEASURES,
    TRIP_UNITS,
    add_result_columns,
    away_trip_effect,
    binned_effect,
    default_season,
    home_away_effect,
    rest_trip_grid,
)
from controllers.charts import COMP_NAMES, effect_figure, rest_trip_heatmap
from controllers.reports import fatigue_report
from controllers.views import (
    club_names,
    competition_names,
    fatigue_table,
    filter_metrics,
    seasons_label,
    upcoming_games,
)
from models.api_model import get_live_games
from models.escudos_model import get_crest_uris
from models.sqlite_model import get_aliases, get_clubs, get_metrics

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

    season = default_season(metrics)  # la base solo tiene la temporada en curso
    st.caption(f"Temporada {seasons_label(season)}")
    c2, c3 = st.columns(2)
    comps = c2.multiselect("Competición", ["ACB", "E", "U"], default=["ACB", "E", "U"],
                           format_func={"ACB": "ACB", "E": "Euroliga", "U": "EuroCup"}.get, key="comps_f")
    only_dual = c3.checkbox("Solo doble competición", value=True, key="dual_f")
    scope = filter_metrics(metrics, season, comps)
    if only_dual:
        scope = scope[scope["dual"]]

    st.subheader("Fuente 1 · SQLite: descanso, carga y rotación por partido")
    st.caption("Los minutos por jugador salen de las estadísticas de Euroliga y EuroCup (API) y de las de la ACB (live.acb.com).")
    fatigue = fatigue_table(scope, names, get_crest_uris())
    st.dataframe(fatigue, width="stretch", hide_index=True, height=320, column_config=image_columns())
    print_table(fatigue)

    current = int(season)
    with st.container(key="keep_api"):
        st.subheader("Fuente 2 · API de Euroliga: próximos partidos")
        st.caption(f"Temporada en curso: {seasons_label(current)}.")
        api_comp = st.radio("Competición de la API", ["E", "U"], horizontal=True,
                            format_func={"E": "Euroliga", "U": "EuroCup"}.get, key="api_comp")
        try:
            live = get_live_games(api_comp, current)
            if live.empty:
                st.info("La API no devuelve partidos para esta temporada.")
            else:
                upcoming = upcoming_games(live, crests=get_crest_uris(), aliases=get_aliases())
                if upcoming.empty:
                    st.info("No quedan partidos por jugar en la temporada en curso.")
                else:
                    st.dataframe(upcoming, width="stretch", hide_index=True, height=260, column_config=image_columns())
                    print_table(upcoming, rows=15)
        except (requests.RequestException, ValueError, KeyError) as exc:  # la app no debe romperse si la API falla
            st.error(f"No se pudo consultar la API de Euroliga: {exc}")

    st.subheader("Gráficos")
    st.caption("Barras: media por tramo con ±1,96 errores estándar. Mide correlación, no causa. Se dibujan todos los tramos: con pocos partidos la barra es poco fiable y con uno solo no tiene barra de error; el número de partidos sale al pasar el cursor y en «Ver los datos del gráfico». Solo la temporada en curso, con los filtros de competición.")
    chart_scope = metrics[metrics["competicion_id"].isin(comps)]
    if only_dual:
        chart_scope = chart_scope[chart_scope["dual"]]
    dark = is_dark()
    if chart_scope.empty:
        st.info("No hay partidos con estos filtros.")
    else:
        with st.container(key="keep_rest"):
            st.markdown("#### Descanso y rotación")
            st.markdown("**Rendimiento según el descanso**")
            rest = binned_effect(chart_scope, "rest_days", "margin_resid")
            st.plotly_chart(effect_figure(rest, "Margen ajustado medio (puntos)", "Días desde el partido anterior", dark),
                            theme=None, width="stretch")
            with st.expander("Ver los datos del gráfico"):
                st.dataframe(competition_names(rest.round(2)), width="stretch", hide_index=True)

        with st.container(key="keep_rot"):
            rot_key = st.selectbox("Medida de rotación", list(ROTATION), format_func=ROTATION.get, key="rot")
            st.markdown(f"**{ROTATION[rot_key]} según los km de los últimos 7 días**")
            rot = binned_effect(chart_scope, "km_7d", rot_key)
            st.plotly_chart(effect_figure(rot, ROTATION[rot_key], "Km de viaje acumulados en 7 días", dark),
                            theme=None, width="stretch")
            with st.expander("Ver los datos del gráfico"):
                st.dataframe(competition_names(rot.round(3)), width="stretch", hide_index=True)

        st.divider()
        with st.container(key="keep_home"):
            st.markdown("#### Resultados y viaje")
            st.caption("Los selectores de esta sección solo cambian las dos últimas gráficas.")
            results = add_result_columns(chart_scope)
            m1, m2 = st.columns(2)
            measure = m1.selectbox("Resultado", list(RESULT_MEASURES), format_func=RESULT_MEASURES.get, key="measure",
                                   help="Se aplica a las dos últimas gráficas. El margen ajustado descuenta la fuerza de los clubes.")
            unit = m2.radio("Medida del viaje", list(TRIP_UNITS), format_func=TRIP_UNITS.get, key="unit",
                            help="Las horas son una estimación: el mejor de autobús (75 km/h) o avión (750 km/h) más 3 h de aeropuerto.")
            label = RESULT_MEASURES[measure]

            st.markdown("**Victorias en casa y fuera**")
            home_away = home_away_effect(results, "win_pct")
            st.plotly_chart(effect_figure(home_away, "Victorias (%)", "Condición del partido", dark),
                            theme=None, width="stretch")
            with st.expander("Ver los datos del gráfico"):
                st.dataframe(competition_names(home_away.round(2)), width="stretch", hide_index=True)

        away_games = results[results["home"] == 0]
        if away_games.empty:
            st.info("No hay partidos fuera con estos filtros.")
        else:
            with st.container(key="keep_trip"):
                st.markdown(f"**{label} fuera de casa según el viaje**")
                by_trip = away_trip_effect(results, unit, measure)
                st.plotly_chart(effect_figure(by_trip, label, TRIP_UNITS[unit], dark), theme=None, width="stretch")
                with st.expander("Ver los datos del gráfico"):
                    st.dataframe(competition_names(by_trip.round(2)), width="stretch", hide_index=True)

            with st.container(key="keep_heat"):
                st.markdown(f"**{label} fuera de casa según descanso y viaje**")
                st.caption("El color compara con la media de los partidos fuera. Las celdas con menos de 15 partidos quedan en blanco.")
                grid = rest_trip_grid(results, measure)
                if grid["media"].notna().any():
                    st.plotly_chart(rest_trip_heatmap(grid, label, float(away_games[measure].mean()), dark),
                                    theme=None, width="stretch")
                else:
                    st.info("Con esta selección ninguna combinación de descanso y viaje reúne 15 partidos. "
                            "Quita «Solo doble competición» o añade competiciones para ver el mapa de calor.")
                with st.expander("Ver los datos del gráfico"):
                    st.dataframe(grid.round(2), width="stretch", hide_index=True)

    user = st.session_state["usuario"]  # el PDF se genera al pulsar, fuera del hilo del script: no puede leer la sesión
    with actions:
        b1, b2, _ = st.columns([3, 3, 4], vertical_alignment="center")
        with b1:
            print_button()
        rot_now = st.session_state.get("rot", "players_10")
        measure_now = st.session_state.get("measure", "win_pct")
        unit_now = st.session_state.get("unit", "km_trip")
        report_filters = {"Temporada": seasons_label(season), "Competiciones": ", ".join(COMP_NAMES[c] for c in comps),
                          "Solo doble competición": "sí" if only_dual else "no"}
        b2.download_button(
            "📄 Exportar a PDF",
            data=lambda: fatigue_report(user, report_filters, fatigue_table(scope, names),
                                        chart_scope, rot_now, ROTATION[rot_now], measure_now, unit_now),
            file_name=f"fatiga_rotaciones_{season}.pdf", mime="application/pdf", type="primary", width="stretch", disabled=chart_scope.empty,
        )
