import streamlit as st

from common.menu import iniciar_pagina
from models.sqlite_model import get_clubs, get_metrics

if iniciar_pagina("Viajes y fatiga", "🏀"):
    st.title("Viajes, descanso y rotaciones en clubes con doble competición")
    st.write(
        "¿Se notan los kilómetros y el poco descanso en los resultados y en las rotaciones de los clubes españoles "
        "que juegan a la vez la ACB y la Euroliga o la EuroCup? La aplicación reúne los calendarios de las tres "
        "competiciones desde 2022/23 y calcula, para cada partido, los días de descanso, los kilómetros de viaje y "
        "cuántos jugadores usa el entrenador."
    )
    metrics, clubs = get_metrics(), get_clubs()
    dual = clubs.groupby(["club_id", "temporada_id"])["competicion_id"].nunique()
    col1, col2, col3 = st.columns(3)
    col1.metric("Partidos jugados", f"{metrics['partido_id'].nunique():,}".replace(",", "."))
    col2.metric("Clubes", clubs["club_id"].nunique())
    col3.metric("Doble competición (club-temporada)", int((dual >= 2).sum()))

    st.subheader("Cómo se usa")
    st.markdown(
        "1. El menú de la izquierda lleva a las dos páginas. «Salir» cierra la sesión.\n"
        "2. Los filtros de cada página (temporada, competición y club) cambian a la vez las tablas y las gráficas.\n"
        "3. Las tablas se ordenan pulsando el título de una columna y se agrandan con el icono de su esquina.\n"
        "4. Bajo cada gráfica, «Ver los datos del gráfico» abre una tabla con los números exactos.\n"
        "5. «Imprimir página» abre el diálogo de impresión del navegador. «Exportar a PDF» descarga un informe con "
        "los datos filtrados que hay en pantalla."
    )

    st.subheader("Qué hay en cada página")
    st.write(
        "Calendario y viajes reúne la tabla de partidos con descanso y kilómetros, el catálogo de sedes con su ciudad "
        "y su país, el ranking de clubes por kilómetros y el mapa de sedes. Al elegir un club, el ranking se "
        "sustituye por las líneas de sus viajes."
    )
    st.write(
        "Fatiga y rotaciones muestra la tabla de descanso, carga y rotación, los próximos partidos que devuelve la "
        "API de Euroliga y dos bloques de gráficas. El primero relaciona el rendimiento y la rotación con el "
        "descanso y los kilómetros. El segundo compara las victorias en casa y fuera y el resultado según el viaje."
    )

    st.subheader("Cómo leer los datos")
    st.markdown(
        "- El descanso son los días desde el partido anterior del club, en cualquier competición.\n"
        "- El viaje se mide en kilómetros de ida y vuelta entre la sede del club y la del partido. En casa vale "
        "cero. Las horas de viaje son una estimación hecha a partir de esos kilómetros.\n"
        "- El margen ajustado es el margen real menos el que se esperaba por la fuerza de los dos clubes y la "
        "ventaja de jugar en casa. Un valor positivo indica que el club rindió por encima de su nivel.\n"
        "- La rotación se mide con los jugadores que superan los 10 minutos, la cuota de minutos de los cinco que "
        "más juegan y los titulares que cambian respecto al partido anterior."
    )

    st.subheader("De dónde salen los datos")
    st.write(
        "Los partidos y los minutos por jugador están en una base SQLite. Las sedes, con sus coordenadas, vienen de "
        "un CSV geocodificado con OpenStreetMap. Los próximos partidos se piden en directo a la API pública de "
        "Euroliga."
    )

    st.info(
        "Los resultados muestran correlaciones, no causas, y con pocos partidos una diferencia puede ser casualidad: "
        "las gráficas indican cuántos partidos hay detrás de cada barra y el mapa de calor deja en blanco las celdas "
        "con menos de 15. Los clubes con doble competición suelen ser los más fuertes, así que sus porcentajes de "
        "victoria salen altos. La rotación solo se conoce en ACB y Euroliga, porque no hay minutos de EuroCup. "
        "Quedan fuera la Champions League, la Copa del Rey y las ligas nacionales de los clubes extranjeros, de modo "
        "que la carga de Unicaja y Tenerife, que juegan la Champions, está subestimada."
    )
