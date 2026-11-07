"""Pruebas de churn.dataset (T004; FR-016, ASUM-DM §3)."""
import pandas as pd
import pytest

from churn import config
from churn.dataset import COLUMNAS, generar, validar


def test_misma_semilla_genera_el_mismo_dataset():
    pd.testing.assert_frame_equal(generar(500, seed=7), generar(500, seed=7))


def test_semilla_distinta_cambia_los_datos():
    assert not generar(500, seed=1).equals(generar(500, seed=2))


def test_columnas_y_tamano():
    df = generar()
    assert list(df.columns) == COLUMNAS
    assert len(df) == config.N_CLIENTES


def test_sin_nulos_ids_unicos_y_dominios_validos():
    df = generar()
    validar(df)  # lanza ValueError si algo falla
    assert df["id_cliente"].is_unique


def test_prevalencia_base_cerca_del_25_por_ciento():
    assert 0.20 <= generar()["churn"].mean() <= 0.30


def test_churn_depende_de_las_variables():
    df = generar()
    por_plan = df.groupby("tipo_plan")["churn"].mean()
    assert por_plan["prepago"] > por_plan["pospago_basico"]
    assert df[df.reclamos_ult_3m >= 3]["churn"].mean() > df[df.reclamos_ult_3m == 0]["churn"].mean()
    assert df[df.renovo_contrato == "si"]["churn"].mean() < df[df.renovo_contrato == "no"]["churn"].mean()
    assert df[df.antiguedad_meses > 48]["churn"].mean() < df[df.antiguedad_meses <= 12]["churn"].mean()


def test_escenario_crisis_sube_cargos_y_reclamos():
    base, crisis = generar(), generar(escenario="crisis")
    assert crisis["cargo_mensual"].mean() > base["cargo_mensual"].mean()
    assert crisis["reclamos_ult_3m"].mean() > base["reclamos_ult_3m"].mean()
    validar(crisis)


def test_escenario_desconocido_se_rechaza():
    with pytest.raises(ValueError, match="escenario"):
        generar(10, escenario="otro")


def test_validar_rechaza_valor_fuera_de_rango():
    df = generar(50)
    df.loc[0, "reclamos_ult_3m"] = 9
    with pytest.raises(ValueError, match="reclamos_ult_3m"):
        validar(df)


def test_csv_fuente_de_verdad_pasa_la_calidad_y_tolera_periodo():
    """T096 (D6): el CSV de data/raw se valida; `periodo` se tolera y no entra al modelo."""
    from churn.features import cargar_datos, validar_calidad
    df = cargar_datos(config.DATA_RAW)
    validar_calidad(df)
    assert len(df) == config.N_CLIENTES and df[config.ID_COL].is_unique
    assert "periodo" not in config.FEATURES
