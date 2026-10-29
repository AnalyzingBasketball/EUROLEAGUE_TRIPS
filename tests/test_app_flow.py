"""Flujo de la interfaz con AppTest de Streamlit: login, sesión y páginas."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from models import api_model

APP_DIR = Path(__file__).resolve().parent.parent
PAGES = ["home.py", "pages/1_calendario_viajes.py", "pages/2_fatiga_rotaciones.py"]


FAKE_GAME = {
    "gameCode": 1, "season": {"year": 2026}, "played": False, "date": "2026-11-05T20:00:00",
    "localDate": "2026-11-05T20:00:00", "utcDate": "2026-11-05T19:00:00Z", "round": 7,
    "phaseType": {"name": "Regular Season"}, "venue": {"code": "X"},
    "local": {"club": {"code": "MAD", "name": "Real Madrid"}}, "road": {"club": {"code": "BAR", "name": "FC Barcelona"}},
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


@pytest.fixture(autouse=True)
def fake_api(monkeypatch):
    """Evita llamadas reales a la API en los tests."""
    import streamlit as st

    st.cache_data.clear()
    monkeypatch.setattr(api_model.requests, "get", lambda *a, **k: FakeResponse({"data": [FAKE_GAME]}))


def _login(at: AppTest, user="admin", password="admin") -> AppTest:
    at.text_input[0].set_value(user)
    at.text_input[1].set_value(password)
    at.button[0].click()
    return at.run()


def _open_page(page: str) -> AppTest:
    """Abre una página desde home.py con sesión iniciada, como haría el menú."""
    at = AppTest.from_file(str(APP_DIR / "home.py"), default_timeout=60)
    at.session_state["usuario"] = "admin"
    return at.switch_page(page).run()


@pytest.mark.parametrize("page", PAGES)
def test_page_requires_login(page):
    at = AppTest.from_file(str(APP_DIR / page), default_timeout=60).run()
    assert not at.exception
    assert len(at.text_input) == 2  # solo el formulario de login
    assert len(at.dataframe) == 0


def test_wrong_password_is_rejected():
    at = _login(AppTest.from_file(str(APP_DIR / "home.py"), default_timeout=60).run(), password="mal")
    assert "usuario" not in at.session_state
    assert any("incorrectos" in e.value for e in at.error)


def test_login_then_logout():
    at = _login(AppTest.from_file(str(APP_DIR / "home.py"), default_timeout=60).run())
    assert at.session_state["usuario"] == "admin"
    assert not at.exception
    salir = next(b for b in at.button if b.label == "Salir")
    salir.click()
    at.run()
    assert "usuario" not in at.session_state


@pytest.mark.parametrize("page,min_charts", [("pages/1_calendario_viajes.py", 2), ("pages/2_fatiga_rotaciones.py", 5)])
def test_pages_show_two_sources_and_charts_after_login(page, min_charts):
    at = _open_page(page)
    assert not at.exception
    assert len(at.dataframe) >= 2
    assert len(at.get("plotly_chart")) >= min_charts
    assert len(at.get("download_button")) == 1  # exportar a PDF
    assert len(at.get("iframe")) == 1  # botón de imprimir
    assert not at.error


def test_selecting_a_club_replaces_ranking_with_trip_map():
    at = _open_page("pages/1_calendario_viajes.py")
    at.selectbox(key="club").select("Real Madrid")
    at.run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 1  # solo el mapa, sin el ranking por club


def test_api_failure_shows_error_not_traceback(monkeypatch):
    def boom(*a, **k):
        raise api_model.requests.ConnectionError("sin red")

    monkeypatch.setattr(api_model.requests, "get", boom)
    at = _open_page("pages/2_fatiga_rotaciones.py")
    assert not at.exception
    assert any("No se pudo consultar la API" in e.value for e in at.error)
