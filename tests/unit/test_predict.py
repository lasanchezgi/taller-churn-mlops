"""Puntuación y niveles de riesgo (T019; FR-001, FR-002, FR-004, FR-016, SC-001)."""
import pytest

from churn import predict


@pytest.mark.parametrize("p,nivel", [(0.0, "bajo"), (0.499, "bajo"), (0.50, "medio"), (0.699, "medio"),
                                     (0.70, "alto"), (1.0, "alto")])
def test_umbrales_de_nivel(p, nivel):
    assert predict.nivel_riesgo(p) == nivel


def test_misma_entrada_y_version_dan_la_misma_probabilidad(ruta_modelo, cliente_valido):
    m = predict.cargar_modelo(ruta_modelo)
    a, b = predict.puntuar(m, cliente_valido), predict.puntuar(m, cliente_valido)
    assert a == b and 0 <= a["probabilidad_churn"] <= 1
    assert a["version_modelo"] == m["card"]["version"]


def test_la_edad_no_altera_la_probabilidad(ruta_modelo, cliente_valido):
    m = predict.cargar_modelo(ruta_modelo)
    sola = predict.puntuar(m, cliente_valido)
    con_edad = predict.puntuar(m, {**cliente_valido, "rango_edad": "60+"})
    assert sola == con_edad


def test_sin_modelo_lanza_error_de_modelo_no_disponible(cliente_valido):
    with pytest.raises(predict.ModeloNoDisponible):
        predict.puntuar(None, cliente_valido)
