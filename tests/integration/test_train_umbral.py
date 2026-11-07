"""Regla del umbral de decisión (T118; FR-027; D4): nunca aborta el entrenamiento."""
import numpy as np
import pytest

from churn import config, train
from churn.dataset import generar

Y = np.array([1, 1, 1, 1, 0, 0, 0, 0])
P = np.array([0.9, 0.8, 0.7, 0.3, 0.6, 0.5, 0.2, 0.1])


def test_camino_1_mayor_precision_con_el_recall_minimo():
    umbral, regla = train.elegir_umbral(Y, P)
    # con umbral 0,7 se capturan 3 de 4 positivos (recall 0,75) sin falsos positivos (precision 1)
    assert umbral == pytest.approx(0.7) and regla == "mayor_precision_con_recall"


def test_camino_2_sin_umbral_viable_toma_el_de_mayor_recall(monkeypatch):
    monkeypatch.setattr(config, "MIN_RECALL", 1.01)  # ningún umbral lo alcanza
    umbral, regla = train.elegir_umbral(Y, P)
    assert regla == "mayor_recall" and umbral == pytest.approx(0.3)  # recall 1,0 con el umbral más alto posible


def test_entrenar_sin_umbral_viable_no_aborta_y_queda_no_aprobado(monkeypatch):
    monkeypatch.setattr(config, "MIN_RECALL", 1.01)
    res = train.entrenar(generar(1500), "logreg")
    card = res["card"]
    assert card["regla_umbral"] == "mayor_recall"
    assert card["criterios_cumplidos"]["recall"] is False
    assert card["aprobado_para_despliegue"] is False
    assert any("recall" in r for r in card["razones_no_aprobado"])


def test_entrenar_normal_usa_la_regla_de_mayor_precision():
    card = train.entrenar(generar(1500), "logreg")["card"]
    # El umbral se calibra con el recall de validación cruzada sobre train; el criterio se mide en prueba
    assert card["regla_umbral"] == "mayor_precision_con_recall"
