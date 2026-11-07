"""Escenarios de drift sobre el CSV (T107; FR-014, SC-009; D6).

Referencia = split de entrenamiento; base = split de prueba; crisis = aplicar_crisis sobre ese split.
"""
import pytest

from churn import config, drift
from churn.features import cargar_datos
from churn.predict import cargar_modelo
from churn.train import entrenar, guardar_modelo


@pytest.fixture(scope="module")
def csv_y_modelo(tmp_path_factory):
    df = cargar_datos(config.DATA_RAW)
    res = entrenar(df, "logreg")
    ruta = tmp_path_factory.mktemp("csv") / "m.joblib"
    guardar_modelo(res, ruta, ruta.parent / "model_card.json")
    return df, cargar_modelo(ruta)


def test_base_del_csv_es_estable(csv_y_modelo, tmp_path):
    df, modelo = csv_y_modelo
    r = drift.simular("base", tmp_path / "d.json", df=df, modelo=modelo)
    assert r["estado_general"] == "estable"
    assert all(v["psi"] < config.PSI_ALERTA for v in r["variables"])


def test_crisis_es_critica_y_solo_por_cargos_y_reclamos(csv_y_modelo, tmp_path):
    df, modelo = csv_y_modelo
    r = drift.simular("crisis", tmp_path / "d.json", df=df, modelo=modelo)
    por = {v["nombre"]: v["nivel"] for v in r["variables"]}
    # Con el CSV, +30 % de cargos mueve el PSI a ~0,23 (alerta) y duplicar reclamos a ~3 (crítico)
    assert r["estado_general"] == "critico" and por["reclamos_ult_3m"] == "critico"
    assert por["cargo_mensual"] in ("alerta", "critico")
    for intacta in ("antiguedad_meses", "uso_datos_gb", "tipo_plan", "metodo_pago", "renovo_contrato"):
        assert por[intacta] == "estable", intacta


def test_base_y_crisis_usan_la_misma_muestra_de_prueba(csv_y_modelo, tmp_path):
    df, modelo = csv_y_modelo
    r = drift.simular("crisis", tmp_path / "d.json", df=df, modelo=modelo)
    assert r["simulacion"]["filas"] == int(len(df) * config.TEST_SIZE)
    assert r["simulacion"]["base"]["informe"]["estado_general"] == "estable"


def test_simular_ya_no_usa_el_generador():
    assert not hasattr(drift, "generar")
