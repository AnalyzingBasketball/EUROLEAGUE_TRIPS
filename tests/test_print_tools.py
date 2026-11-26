"""Tabla estática de impresión: sin imágenes, sin decimales sobrantes y con límite de filas."""
import pandas as pd

from common import print_tools


def test_print_table_limita_filas_y_quita_imagenes(monkeypatch):
    salida: list[str] = []
    monkeypatch.setattr(print_tools.st, "html", salida.append)
    tabla = pd.DataFrame({"Escudo": ["data:x"] * 5, "Club": list("abcde"), "Km": [10.0, 20.0, 30.5, None, 5.0]})
    print_tools.print_table(tabla, rows=3)
    html = salida[0]
    assert "data:x" not in html and "Escudo" not in html
    assert "<td>10</td>" in html and "<td>30.5</td>" in html
    assert "Se imprimen las 3 primeras filas de 5." in html
    assert "<td>d</td>" not in html
