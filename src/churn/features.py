"""Carga, calidad, partición y preprocesamiento de features (T010, FR-006, FR-008, FR-016)."""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from churn import config
from churn.dataset import ANTIGUEDAD, CARGO, RECLAMOS, USO_DATOS


class DataQualityError(ValueError):
    """Los datos no cumplen el esquema, los rangos o los dominios esperados."""


# Columnas obligatorias: features, objetivo y atributo sensible (solo para auditar)
REQUERIDAS = [*config.FEATURES, config.TARGET, config.SENSITIVE_COL]
RANGOS = {
    "antiguedad_meses": ANTIGUEDAD,
    "cargo_mensual": CARGO,
    "reclamos_ult_3m": RECLAMOS,
    "uso_datos_gb": USO_DATOS,
}
DOMINIOS = {
    "tipo_plan": config.PLANES,
    "metodo_pago": config.METODOS_PAGO,
    "renovo_contrato": config.RENOVACION,
    config.SENSITIVE_COL: config.RANGOS_EDAD,
    config.TARGET: [0, 1],
}


def cargar_datos(ruta=config.DATA_RAW) -> pd.DataFrame:
    """Lee el CSV; si no existe, falla con un mensaje claro."""
    try:
        return pd.read_csv(ruta)
    except FileNotFoundError as e:
        raise DataQualityError(f"no existe el archivo de datos: {ruta}") from e


def validar_calidad(df: pd.DataFrame) -> None:
    """Lanza DataQualityError por columnas faltantes, nulos, rangos o categorías no permitidas."""
    faltan = [c for c in REQUERIDAS if c not in df.columns]
    if faltan:
        raise DataQualityError(f"faltan columnas: {faltan}")
    nulos = df[REQUERIDAS].isna().sum()
    nulos = nulos[nulos > 0]
    if not nulos.empty:
        raise DataQualityError(f"nulos en: {nulos.to_dict()}")
    for col, (lo, hi) in RANGOS.items():
        if not df[col].between(lo, hi).all():
            raise DataQualityError(f"{col}: valores fuera del rango {lo}–{hi}")
    for col, validos in DOMINIOS.items():
        fuera = set(df[col].unique()) - set(validos)
        if fuera:
            raise DataQualityError(
                f"{col}: categorías no permitidas {sorted(map(str, fuera))}; use {validos}"
            )


def particionar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Partición entrenamiento/prueba estratificada por churn, con la semilla fija."""
    return train_test_split(
        df, test_size=config.TEST_SIZE, stratify=df[config.TARGET],
        random_state=config.SEED,
    )


def construir_preprocesador(excluir: tuple = ()) -> ColumnTransformer:
    """Escala las numéricas y codifica las categóricas; descarta el resto (incluida la edad).

    `excluir` quita features solo para la revisión de proxies (FR-024); por defecto usa todas.
    """
    num = [c for c in config.NUMERIC_FEATURES if c not in excluir]
    cat = [c for c in config.CATEGORICAL_FEATURES if c not in excluir]
    return ColumnTransformer(
        [
            ("num", StandardScaler(), num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ],
        remainder="drop",
    )
