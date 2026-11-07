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


def test_se_calcula_solo_con_el_split_de_entrenamiento(datos, perfil):
    tr, _ = particionar(datos)
    assert perfil == perfil_referencia(tr[config.FEATURES])
