"""aplicar_crisis (T105; FR-014, FR-016; D6): cargos y reclamos más altos sobre los mismos clientes."""
import numpy as np
import pandas as pd

from churn.dataset import aplicar_crisis, generar


def test_sube_cargos_un_30_por_ciento_y_duplica_reclamos():
    df = generar(500, seed=3)
    c = aplicar_crisis(df)
    esperado = np.clip((df["cargo_mensual"] * 1.3).round(2), 10, 1000)
    pd.testing.assert_series_equal(c["cargo_mensual"], esperado)
    assert (c["reclamos_ult_3m"] == np.minimum(df["reclamos_ult_3m"] * 2, 6)).all()


def test_no_toca_otras_columnas_ni_el_original():
    df = generar(300, seed=4)
    copia = df.copy()
    c = aplicar_crisis(df)
    pd.testing.assert_frame_equal(df, copia)
    otras = [col for col in df.columns if col not in ("cargo_mensual", "reclamos_ult_3m")]
    pd.testing.assert_frame_equal(c[otras], df[otras])


def test_es_determinista():
    df = generar(200, seed=5)
    pd.testing.assert_frame_equal(aplicar_crisis(df), aplicar_crisis(df))
