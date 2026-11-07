"""Perfil de referencia del model card (T049, T052; FR-014, SC-009; D6)."""
import pytest

from churn import config
from churn.dataset import generar
from churn.features import particionar
from churn.train import entrenar, perfil_referencia


@pytest.fixture(scope="module")
def datos():
    return generar(1500)


@pytest.fixture(scope="module")
def perfil(datos):
    return entrenar(datos, "logreg")["card"]["perfil_referencia"]


def test_trae_las_7_variables(perfil):
    assert set(perfil) == set(config.FEATURES)


def test_numericas_tienen_hasta_9_limites_y_frecuencias_que_suman_1(perfil):
    for col in config.NUMERIC_FEATURES:
        p = perfil[col]
        assert p["tipo"] == "numerica" and 1 <= len(p["limites"]) <= 9
        assert len(p["frecuencias"]) == len(p["limites"]) + 1
        assert sum(p["frecuencias"]) == pytest.approx(1)


def test_categoricas_traen_la_proporcion_por_categoria(perfil):
    for col, dominio in (("tipo_plan", config.PLANES), ("metodo_pago", config.METODOS_PAGO),
                         ("renovo_contrato", config.RENOVACION)):
        f = perfil[col]["frecuencias"]
        assert set(f) <= set(dominio) and sum(f.values()) == pytest.approx(1)


def test_los_limites_son_los_deciles_reales_y_se_quitan_repetidos():
    import numpy as np
    import pandas as pd

    X = pd.DataFrame({
        "antiguedad_meses": np.arange(1, 101), "cargo_mensual": np.arange(1, 101, dtype=float),
        "reclamos_ult_3m": [0] * 95 + [1] * 5, "uso_datos_gb": np.arange(1, 101, dtype=float),
        "tipo_plan": ["prepago"] * 100, "metodo_pago": ["efectivo"] * 100, "renovo_contrato": ["si"] * 100,
    })
    p = perfil_referencia(X)
    assert p["antiguedad_meses"]["limites"] == pytest.approx(np.quantile(np.arange(1, 101), np.linspace(0.1, 0.9, 9)))
    assert p["antiguedad_meses"]["frecuencias"] == pytest.approx([0.1] * 10, abs=0.011)
    assert p["reclamos_ult_3m"]["limites"] == [0.0]  # 9 deciles iguales a 0 → un solo límite
    assert p["reclamos_ult_3m"]["frecuencias"] == pytest.approx([0.0, 1.0])  # intervalos [a, b), igual que drift.py: el 0 cae en [0, ∞)
    assert p["tipo_plan"]["frecuencias"] == {"prepago": 1.0}


def test_se_calcula_solo_con_el_split_de_entrenamiento(datos, perfil):
    tr, _ = particionar(datos)
    assert perfil == perfil_referencia(tr[config.FEATURES])
