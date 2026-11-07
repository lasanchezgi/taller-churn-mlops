"""Pruebas de churn.evaluate (T006/T011; FR-018, SC-004, SC-010)."""
import numpy as np
import pytest

from churn import config
from churn.evaluate import metricas_equidad, metricas_negocio, metricas_tecnicas

# Caso calculado a mano con umbral 0,5: pred = [1, 1, 0, 0, 1, 0]
Y = np.array([1, 0, 1, 0, 1, 0])
P = np.array([0.9, 0.6, 0.4, 0.2, 0.7, 0.1])


def test_metricas_tecnicas_contra_calculo_manual():
    m = metricas_tecnicas(Y, P, 0.5)
    # tp=2, fp=1, fn=1, tn=2
    assert m["matriz_confusion"] == {"tn": 2, "fp": 1, "fn": 1, "tp": 2}
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["f1"] == pytest.approx(2 / 3)
    assert m["roc_auc"] == pytest.approx(8 / 9)


def test_umbral_igual_a_la_probabilidad_cuenta_como_positivo():
    assert metricas_tecnicas(Y, P, 0.9)["matriz_confusion"]["tp"] == 1


def test_negocio_clientes_e_ingresos_en_riesgo():
    cargo = np.array([100.0, 50.0, 80.0, 20.0, 30.0, 10.0])
    m = metricas_negocio(P, cargo, 0.5)
    assert m["clientes_en_riesgo"] == 3
    assert m["ingresos_mensuales_en_riesgo"] == pytest.approx(180.0)
    assert m["ingresos_6_meses_en_riesgo"] == pytest.approx(1080.0)


def test_negocio_prioriza_segun_presupuesto():
    p = np.full(400, 0.9)
    m = metricas_negocio(p, np.full(400, 10.0), 0.5)
    assert m["max_contactos"] == int(config.PRESUPUESTO_CAMPANA // config.COSTO_CONTACTO) == 250
    assert m["clientes_priorizados"] == 250
    assert m["costo_campana"] == pytest.approx(2000.0)


def test_negocio_prioriza_menos_si_hay_pocos_en_riesgo():
    m = metricas_negocio(P, np.full(6, 10.0), 0.5)
    assert m["clientes_priorizados"] == 3
    assert m["costo_campana"] == pytest.approx(3 * config.COSTO_CONTACTO)


def test_negocio_presupuesto_y_costo_propios():
    m = metricas_negocio(P, np.full(6, 10.0), 0.5, presupuesto=16.0, costo=8.0)
    assert m["max_contactos"] == 2 and m["clientes_priorizados"] == 2


def test_equidad_por_grupo_y_ratio_de_impacto_dispar():
    g = np.array(["a", "a", "a", "b", "b", "b"])
    m = metricas_equidad(Y, P, g, 0.5)
    # a: pred [1,1,0] → selección 2/3, recall 1/2 · b: pred [0,1,0] → selección 1/3, recall 1/1
    assert m["grupos"]["a"]["tasa_seleccion"] == pytest.approx(2 / 3)
    assert m["grupos"]["b"]["tasa_seleccion"] == pytest.approx(1 / 3)
    assert m["grupos"]["a"]["recall"] == pytest.approx(1 / 2)
    assert m["grupos"]["b"]["recall"] == pytest.approx(1.0)
    assert m["grupos"]["a"]["n"] == 3
    assert m["ratio_impacto_dispar"] == pytest.approx(0.5)
    assert m["dif_max_recall"] == pytest.approx(0.5)


def test_equidad_grupo_sin_positivos_no_inventa_recall():
    g = np.array(["a", "a", "a", "b", "b", "b"])
    y = np.array([1, 0, 1, 0, 0, 0])
    m = metricas_equidad(y, P, g, 0.5)
    assert m["grupos"]["b"]["recall"] is None


def test_equidad_sin_seleccionados_no_divide_por_cero():
    g = np.array(["a"] * 3 + ["b"] * 3)
    m = metricas_equidad(Y, P, g, 0.99)
    assert m["ratio_impacto_dispar"] is None
