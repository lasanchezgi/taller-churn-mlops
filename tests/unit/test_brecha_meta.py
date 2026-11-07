"""scripts/brecha_meta.py: fórmula de la brecha de −3 pp (ASUM-DM §1.4; D10)."""
import importlib.util

import pytest

from churn import config


def _modulo():
    spec = importlib.util.spec_from_file_location("brecha_meta", config.ROOT / "scripts" / "brecha_meta.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_formula_de_retenidos_y_baja_en_pp():
    m = _modulo()
    assert m.retenidos(250, 0.758) == pytest.approx(56.85)
    assert m.baja_pp(250, 0.758) == pytest.approx(1.137)  # 100 × 56,85 / 5.000
    assert m.baja_pp(250, 0.40) == pytest.approx(0.60)    # con la precision mínima aceptada


def test_la_meta_de_3_pp_no_se_alcanza_con_250_contactos_ni_con_precision_perfecta():
    assert _modulo().baja_pp(250, 1.0) < 3


def test_precision_a_escala_usa_k_proporcional_a_la_base():
    y = [1, 0, 1, 0] * 25
    proba = [i / 100 for i in range(100)][::-1]
    k, p = _modulo().precision_a_escala(y, proba, 250, base=1000)
    assert k == 25 and p == pytest.approx(sum(y[:25]) / 25)
