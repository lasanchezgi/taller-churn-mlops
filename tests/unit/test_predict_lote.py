"""predict.puntuar_lote (T028; FR-009, FR-016)."""
import pytest

from churn import predict


def test_conserva_el_orden_y_coincide_con_la_individual(ruta_modelo, clientes_lote):
    modelo = predict.cargar_modelo(ruta_modelo)
    clientes = clientes_lote(50)
    lote = predict.puntuar_lote(modelo, clientes)
    assert len(lote) == 50
    for cliente, res in zip(clientes, lote):
        unico = predict.puntuar(modelo, cliente)
        assert res["probabilidad_churn"] == pytest.approx(unico["probabilidad_churn"])
        assert res["nivel_riesgo"] == unico["nivel_riesgo"]


def test_sin_modelo_lanza_modelo_no_disponible(clientes_lote):
    with pytest.raises(predict.ModeloNoDisponible):
        predict.puntuar_lote(None, clientes_lote(3))
