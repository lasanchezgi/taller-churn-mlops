"""Pruebas de churn.features (T005/T010; FR-006, FR-008, FR-016)."""
import numpy as np
import pytest

from churn import config
from churn.dataset import generar
from churn.features import (
    DataQualityError, cargar_datos, construir_preprocesador, particionar, validar_calidad,
)


@pytest.fixture
def df():
    return generar(1000)


def test_datos_validos_pasan(df):
    validar_calidad(df)


def test_rechaza_columna_faltante(df):
    with pytest.raises(DataQualityError, match="faltan columnas"):
        validar_calidad(df.drop(columns=["cargo_mensual"]))


def test_rechaza_nulos(df):
    df.loc[0, "tipo_plan"] = None
    with pytest.raises(DataQualityError, match="nulos"):
        validar_calidad(df)


def test_rechaza_valor_fuera_de_rango(df):
    df.loc[0, "antiguedad_meses"] = 121
    with pytest.raises(DataQualityError, match="antiguedad_meses"):
        validar_calidad(df)


def test_rechaza_categoria_no_permitida(df):
    df.loc[0, "metodo_pago"] = "cripto"
    with pytest.raises(DataQualityError, match="metodo_pago"):
        validar_calidad(df)


def test_carga_archivo_inexistente(tmp_path):
    with pytest.raises(DataQualityError, match="no existe"):
        cargar_datos(tmp_path / "nada.csv")


def test_cargar_datos_lee_el_csv(tmp_path, df):
    ruta = tmp_path / "d.csv"
    df.to_csv(ruta, index=False)
    assert len(cargar_datos(ruta)) == len(df)


def test_particion_estratificada_y_reproducible(df):
    tr, te = particionar(df)
    assert len(te) == int(len(df) * config.TEST_SIZE)
    assert abs(tr.churn.mean() - te.churn.mean()) < 0.01
    assert set(tr.id_cliente).isdisjoint(te.id_cliente)
    tr2, _ = particionar(df)
    assert list(tr.id_cliente) == list(tr2.id_cliente)


def test_preprocesador_usa_solo_features_y_no_la_edad(df):
    pre = construir_preprocesador()
    usadas = [c for _, _, cols in pre.transformers for c in cols]
    assert usadas == config.FEATURES
    assert config.SENSITIVE_COL not in usadas
    X = pre.fit_transform(df)  # df trae rango_edad y churn, que se ignoran
    assert X.shape[1] == 4 + 3 + 4 + 2  # 4 numéricas + one-hot de plan, pago y renovó


def test_preprocesador_ignora_categoria_desconocida(df):
    pre = construir_preprocesador().fit(df)
    nuevo = df.head(1).copy()
    nuevo["tipo_plan"] = "otro"
    X = pre.transform(nuevo)
    assert not np.isnan(X).any()
