import streamlit as st

from common.menu import iniciar_pagina
from models.sqlite_model import get_clubs, get_metrics

if iniciar_pagina("Viajes y fatiga", "🏀"):
    st.title("Viajes, descanso y rotaciones en clubes con doble competición")
    st.write(
        "¿Pesan los kilómetros y el poco descanso en los resultados y en las rotaciones de los clubes españoles "
        "que compiten a la vez en ACB y en Euroliga o EuroCup? La aplicación reúne los calendarios de las tres "
        "competiciones desde 2022/23 y calcula, para cada partido, el descanso, los kilómetros de viaje y la "
        "rotación de la plantilla."
    )
    metrics, clubs = get_metrics(), get_clubs()
    dual = clubs.groupby(["club_id", "temporada_id"])["competicion_id"].nunique()
    col1, col2, col3 = st.columns(3)
    col1.metric("Partidos jugados", f"{metrics['partido_id'].nunique():,}".replace(",", "."))
    col2.metric("Clubes", clubs["club_id"].nunique())
    col3.metric("Doble competición (club-temporada)", int((dual >= 2).sum()))
    st.info(
        "Los resultados muestran correlaciones, no causas. Quedan fuera la Champions League, la Copa del Rey y las "
        "ligas domésticas de los clubes extranjeros."
    )
