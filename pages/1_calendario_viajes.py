import streamlit as st

from common.menu import image_columns, iniciar_pagina, number_formats
from common.print_tools import print_button
from common.theme import is_dark
from controllers.chart_data import default_season, km_by_club, trip_lines, venue_counts
from controllers.charts import km_by_club_figure, trip_map_figure
from controllers.map_charts import animated_map_figure, detail_map_figure
from controllers.map_data import (
    TOP_ROUTES,
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

if iniciar_pagina("Calendario y viajes", "✈️"):
    st.title("Calendario y viajes")
    actions = st.container()
    metrics, clubs, venues = get_metrics(), get_clubs(), get_venues()
    names = club_names(clubs)

    c1, c2, c3 = st.columns(3)
    seasons = sorted(metrics["temporada_id"].unique(), reverse=True)
    season = c1.selectbox("Temporada", seasons, index=seasons.index(default_season(metrics)),
                          format_func=seasons_label, key="season")
    comps = c2.multiselect("Competición", list(COMPETITIONS), default=list(COMPETITIONS),
                           format_func=COMPETITIONS.get, key="comps")
    in_season = clubs[clubs["temporada_id"] == season].drop_duplicates("club_id")
    options = {"Todos": None} | {r.club: r.club_id for r in in_season.sort_values("club").itertuples()}
    club_label = c3.selectbox("Club", list(options), key="club")
    filtered = filter_metrics(metrics, season, comps, options[club_label])

    st.subheader("Fuente 1 · SQLite: partidos jugados y kilómetros")
    st.caption("Un partido aparece dos veces, una por cada club. Km del viaje: ida y vuelta entre la sede base y la del partido.")
    flags = get_flag_uris()
    st.dataframe(trip_table(filtered, names, venues, get_crest_uris(), flags), width="stretch", hide_index=True,
                 height=320, column_config=image_columns())

    st.subheader("Fuente 2 · CSV: sedes y coordenadas")
    st.caption("Geocodificadas con OpenStreetMap (ODbL). Las filas con «revisar» tienen una coordenada aproximada.")
    st.dataframe(
        venues_table(get_venues_csv(), flags), width="stretch", hide_index=True, height=260,
        column_config=number_formats(Latitud="%.4f", Longitud="%.4f") | image_columns(),
    )

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
            lines = None
        else:
            lines = trip_lines(filtered, venues)
        st.markdown("**Mapa de sedes y viajes**")
        m1, m2 = st.columns(2)
        view = m1.radio("Vista del mapa", ["Temporada completa", "Animación por meses"], horizontal=True, key="map_view")
        ground = m2.radio("Fondo del mapa", ["Detallado", "Simple"], horizontal=True, key="map_ground",
                          help="El fondo detallado descarga las teselas de Carto. Si no cargan, el simple no necesita conexión.")
        club_chosen = options[club_label] is not None
        if ground == "Simple":
            counts = venue_counts(filtered, venues)
            st.plotly_chart(trip_map_figure(counts, lines, dark), theme=None, width="stretch")
            if counts["revisar"].any():
                st.caption("Algunas sedes tienen coordenada aproximada (ciudad): el punto puede desviarse unos kilómetros.")
        elif view == "Animación por meses":
            frames = month_frames(filtered, venues, names, with_routes=club_chosen)
            st.plotly_chart(animated_map_figure(frames, dark), theme=None, width="stretch")
            st.caption("Pulsa Reproducir o arrastra el control: cada mes suma los partidos jugados hasta entonces."
                       + ("" if club_chosen else " Elige un club para ver también sus viajes."))
        else:
            stats = venue_stats(filtered, venues, names)
            routes = route_lines(filtered, venues, None if club_chosen else TOP_ROUTES)
            choices = venue_options(stats)
            venue_id = st.selectbox("Ver los partidos de una sede (se resalta en el mapa)", [None, *choices],
                                    format_func=lambda i: "Ninguna" if i is None else choices[i], key="venue_pick")
            st.plotly_chart(detail_map_figure(stats, routes, dark, venue_id), theme=None, width="stretch")
            st.caption("Pasa el cursor por una sede para ver sus partidos y clubes. La leyenda enciende y apaga cada competición. "
                       + ("Se dibujan todos los viajes del club." if club_chosen
                          else f"Se dibujan las {TOP_ROUTES} rutas más repetidas; elige un club para ver las suyas."))
            if venue_id is not None:
                games_here = venue_games(filtered, venue_id, names, get_crest_uris())
                st.markdown(f"**Partidos en {venues.set_index('id')['nombre'][venue_id]}** ({len(games_here)})")
                st.dataframe(games_here, width="stretch", hide_index=True, height=260, column_config=image_columns())

    user = st.session_state["usuario"]  # el PDF se genera al pulsar, fuera del hilo del script: no puede leer la sesión
    with actions:
        b1, b2, _ = st.columns([3, 3, 4], vertical_alignment="center")
        with b1:
            print_button()
        trips = trip_table(filtered, names, venues).drop(columns="País")  # el PDF ya va justo de ancho
        km_data = km_by_club(filtered, names) if options[club_label] is None and not filtered.empty else None
        trip_data = trip_lines(filtered, venues) if options[club_label] is not None and not filtered.empty else None
        report_filters = {"Temporada": seasons_label(season), "Competiciones": ", ".join(COMPETITIONS[c] for c in comps),
                          "Club": club_label}
        b2.download_button(
            "📄 Exportar a PDF",
            data=lambda: trip_report(user, report_filters, trips, km_data,
                                     venue_counts(filtered, venues), trip_data),
            file_name=f"calendario_viajes_{season}.pdf", mime="application/pdf", type="primary", width="stretch", disabled=filtered.empty,
        )
