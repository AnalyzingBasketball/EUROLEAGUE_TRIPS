import streamlit as st

from common.menu import image_columns, iniciar_pagina, number_formats
from common.print_tools import print_button, print_table
from common.theme import is_dark
from controllers.chart_data import default_season, km_by_club, venue_counts
from controllers.charts import km_by_club_figure, trip_map_figure
from controllers.map_charts import animated_map_figure, detail_map_figure
from controllers.map_data import (
    month_frames,
    route_lines,
    venue_games,
    venue_options,
    venue_stats,
)
from controllers.reports import trip_report
from controllers.views import (
    club_names,
    competition_names,
    filter_metrics,
    seasons_label,
    trip_table,
    venues_table,
)
from models.banderas_model import get_flag_uris
from models.csv_model import get_venues_csv
from models.escudos_model import get_crest_uris
from models.sqlite_model import get_clubs, get_metrics, get_venues

COMPETITIONS = {"ACB": "ACB", "E": "Euroliga", "U": "EuroCup"}

if iniciar_pagina("Calendario y viajes"):
    st.title("Calendario y viajes")
    actions = st.container()
    metrics, clubs, venues = get_metrics(), get_clubs(), get_venues()
    names = club_names(clubs)

    season = default_season(metrics)  # la base solo tiene la temporada en curso
    st.caption(f"Temporada {seasons_label(season)}")
    c2, c3 = st.columns(2)
    comps = c2.multiselect("Competición", list(COMPETITIONS), default=list(COMPETITIONS),
                           format_func=COMPETITIONS.get, key="comps")
    in_season = clubs[clubs["temporada_id"] == season].drop_duplicates("club_id")
    options = {"Todos": None} | {r.club: r.club_id for r in in_season.sort_values("club").itertuples()}
    club_label = c3.selectbox("Club", list(options), key="club")
    filtered = filter_metrics(metrics, season, comps, options[club_label])

    st.subheader("Fuente 1 · SQLite: partidos jugados y kilómetros")
    st.caption("Un partido aparece dos veces, una por cada club. Km del viaje: ida y vuelta entre la sede base y la del partido.")
    flags = get_flag_uris()
    trips = trip_table(filtered, names, venues, get_crest_uris(), flags)
    st.dataframe(trips, width="stretch", hide_index=True, height=320, column_config=image_columns())
    print_table(trips)

    with st.container(key="keep_sedes"):
        st.subheader("Fuente 2 · CSV: sedes y coordenadas")
        st.caption("Geocodificadas con OpenStreetMap (ODbL). Las filas con «revisar» tienen una coordenada aproximada.")
        venue_list = venues_table(get_venues_csv(), flags)
        st.dataframe(venue_list, width="stretch", hide_index=True, height=260,
                     column_config=number_formats(Latitud="%.4f", Longitud="%.4f") | image_columns())
        print_table(venue_list, rows=20)

    with st.container(key="keep_km"):
        st.subheader("Gráficos")
        if filtered.empty:
            st.info("No hay partidos jugados con estos filtros.")
        else:
            dark = is_dark()
            if options[club_label] is None:
                st.markdown("**Km de viaje acumulados por club** (los 20 con más km)")
                km = km_by_club(filtered, names)
                st.plotly_chart(km_by_club_figure(km, dark), theme=None, width="stretch")
                with st.expander("Ver los datos del gráfico"):
                    st.dataframe(competition_names(km.round(0), "Competición"), width="stretch", hide_index=True)
    if not filtered.empty:
        with st.container(key="keep_map"):
            st.markdown("**Mapa de sedes y viajes**")
            m1, m2 = st.columns(2)
            view = m1.radio("Vista del mapa", ["Temporada completa", "Animación por meses"], horizontal=True, key="map_view")
            ground = m2.radio("Fondo del mapa", ["Detallado", "Simple"], horizontal=True, key="map_ground",
                              help="El fondo detallado descarga las teselas de Carto. Si no cargan, el simple no necesita conexión.")
            if ground == "Simple":
                counts = venue_counts(filtered, venues)
                st.plotly_chart(trip_map_figure(counts, route_lines(filtered, venues), dark), theme=None, width="stretch")
                if counts["revisar"].any():
                    st.caption("Algunas sedes tienen coordenada aproximada (ciudad): el punto puede desviarse unos kilómetros.")
            elif view == "Animación por meses":
                frames = month_frames(filtered, venues, names)
                st.plotly_chart(animated_map_figure(frames, dark), theme=None, width="stretch")
                st.caption("Pulsa Reproducir o arrastra el control: cada mes suma los partidos jugados y los viajes hechos hasta entonces.")
            else:
                stats = venue_stats(filtered, venues, names)
                routes = route_lines(filtered, venues)
                choices = venue_options(stats)
                venue_id = st.selectbox("Ver los partidos de una sede (se resalta en el mapa)", [None, *choices],
                                        format_func=lambda i: "Ninguna" if i is None else choices[i], key="venue_pick")
                st.plotly_chart(detail_map_figure(stats, routes, dark, venue_id), theme=None, width="stretch")
                st.caption(f"Se dibujan todos los desplazamientos ({len(routes)} rutas distintas, {int(routes['veces'].sum())} viajes): "
                           "de la sede base de cada club a la del partido. Pasa el cursor por una sede o por el punto central de una "
                           "línea para ver sus datos. La leyenda enciende y apaga cada competición; elige un club para ver solo los suyos.")
                if venue_id is not None:
                    games_here = venue_games(filtered, venue_id, names, get_crest_uris())
                    st.markdown(f"**Partidos en {venues.set_index('id')['nombre'][venue_id]}** ({len(games_here)})")
                    st.dataframe(games_here, width="stretch", hide_index=True, height=260, column_config=image_columns())
                    print_table(games_here, rows=15)

    user = st.session_state["usuario"]  # el PDF se genera al pulsar, fuera del hilo del script: no puede leer la sesión
    with actions:
        b1, b2, _ = st.columns([3, 3, 4], vertical_alignment="center")
        with b1:
            print_button()
        trips = trip_table(filtered, names, venues).drop(columns="País")  # el PDF ya va justo de ancho
        km_data = km_by_club(filtered, names) if options[club_label] is None and not filtered.empty else None
        pdf_routes = route_lines(filtered, venues) if not filtered.empty else None
        report_filters = {"Temporada": seasons_label(season), "Competiciones": ", ".join(COMPETITIONS[c] for c in comps),
                          "Club": club_label}
        b2.download_button(
            "Exportar a PDF",
            data=lambda: trip_report(user, report_filters, trips, km_data,
                                     venue_counts(filtered, venues), pdf_routes),
            file_name=f"calendario_viajes_{season}.pdf", mime="application/pdf", type="primary", width="stretch", disabled=filtered.empty,
        )
