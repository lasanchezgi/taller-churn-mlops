"""Intento único de mitigación de equidad (T122; FR-024, SC-010; D2)."""
import json

from churn import config, mitigacion
from churn.dataset import generar

NOMBRES = {"base_logreg", "sin_metodo_pago", "sin_tipo_plan", "sin_antiguedad_meses", "rf"}


def test_compara_lr_rf_y_el_modelo_sin_cada_proxy():
    r = mitigacion.ejecutar(generar(1200))
    assert {v["nombre"] for v in r["variantes"]} == NOMBRES
    for v in r["variantes"]:
        assert {"recall", "dif_max_recall", "ratio_impacto_dispar", "umbral"} <= v.keys()
        assert config.SENSITIVE_COL not in v["features"]  # la edad nunca es predictor
        assert isinstance(v["umbral"], float)               # un solo umbral: nada por grupo


def test_mide_la_asociacion_de_cada_feature_con_la_edad():
    r = mitigacion.ejecutar(generar(1200))
    assert set(r["asociacion_con_edad"]) == set(config.FEATURES)
    assert all(0 <= v <= 1 for v in r["asociacion_con_edad"].values())


def test_informa_tamano_y_positivos_por_grupo_y_una_conclusion():
    r = mitigacion.ejecutar(generar(1200))
    assert set(r["grupos"]) == set(config.RANGOS_EDAD)
    assert all({"n", "positivos"} <= g.keys() for g in r["grupos"].values())
    assert r["conclusion"]


def test_la_conclusion_no_fuerza_si_ninguna_variante_cumple(monkeypatch):
    monkeypatch.setattr(config, "MAX_DIF_RECALL", -1.0)  # imposible de cumplir
    r = mitigacion.ejecutar(generar(1200))
    assert r["alguna_variante_cumple"] is False and "no se fuerza" in r["conclusion"]


def test_es_determinista():
    assert mitigacion.ejecutar(generar(1000)) == mitigacion.ejecutar(generar(1000))


def test_main_escribe_el_json(tmp_path, monkeypatch):
    csv = tmp_path / "d.csv"
    generar(1000).to_csv(csv, index=False)
    monkeypatch.setattr(config, "DATA_RAW", csv)
    monkeypatch.setattr(config, "MITIGACION_PATH", tmp_path / "m.json", raising=False)
    mitigacion.main([])
    assert set(json.loads((tmp_path / "m.json").read_text())) >= {"variantes", "conclusion"}
