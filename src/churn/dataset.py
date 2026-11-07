"""Generación y validación del dataset sintético de churn (T009, FR-016, ASUM-DM §3).

Uso: python -m churn.dataset [--escenario base|crisis] [--forzar]
"""
import argparse

import numpy as np
import pandas as pd

from churn import config

ESCENARIOS = ("base", "crisis")
# Orden de columnas del dataset
COLUMNAS = [
    "id_cliente", "antiguedad_meses", "tipo_plan", "cargo_mensual",
    "reclamos_ult_3m", "uso_datos_gb", "metodo_pago", "renovo_contrato",
    "rango_edad", "churn",
]
# Límites de entrada (FR-006)
ANTIGUEDAD = (1, 120)
CARGO = (10.0, 1000.0)
RECLAMOS = (0, 6)
USO_DATOS = (0.0, 1000.0)

# Intercepto del logit: calibrado para ~25 % de churn en el escenario base
INTERCEPTO = -1.05


def _sigmoide(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generar(n: int = config.N_CLIENTES, seed: int = config.SEED,
            escenario: str = "base") -> pd.DataFrame:
    """Devuelve n clientes sintéticos; misma semilla y escenario, mismo resultado.

    Solo para demos y pruebas: la fuente de entrenamiento es data/raw/churn_telco.csv (D6).
    """
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario '{escenario}' no válido; use uno de {list(ESCENARIOS)}")
    rng = np.random.default_rng(seed)
    crisis = escenario == "crisis"

    plan = rng.choice(config.PLANES, size=n, p=[0.35, 0.45, 0.20])
    es_prepago = plan == "prepago"
    antiguedad = np.clip(rng.exponential(30, n).round() + 1, *ANTIGUEDAD).astype(int)

    # Cargo según plan; en crisis sube 30 %
    base_cargo = np.select([es_prepago, plan == "pospago_basico"], [20.0, 55.0], 110.0)
    cargo = base_cargo * rng.lognormal(0.0, 0.25, n) * (1.3 if crisis else 1.0)
    cargo = np.clip(cargo, *CARGO).round(2)

    # Reclamos: Poisson; en crisis se duplica la tasa
    lam = (0.5 + 0.3 * es_prepago) * (2.0 if crisis else 1.0)
    reclamos = np.clip(rng.poisson(lam), *RECLAMOS).astype(int)

    uso = np.clip(rng.gamma(2.0, np.where(es_prepago, 2.0, 6.0)), *USO_DATOS).round(2)
    pago = np.where(
        es_prepago,
        rng.choice(config.METODOS_PAGO, size=n, p=[0.05, 0.05, 0.60, 0.30]),
        rng.choice(config.METODOS_PAGO, size=n, p=[0.40, 0.35, 0.05, 0.20]),
    )
    renovo = np.where(rng.random(n) < np.where(es_prepago, 0.30, 0.65), "si", "no")
    edad = rng.choice(config.RANGOS_EDAD, size=n, p=[0.15, 0.35, 0.35, 0.15])

    # Churn: más reclamos, prepago y cargo alto suben el riesgo; renovar y antigüedad lo bajan
    logit = (
        INTERCEPTO
        + 0.55 * reclamos
        + 0.90 * es_prepago
        - 0.90 * (renovo == "si")
        - 0.020 * antiguedad
        + 0.005 * (cargo - 50)
        + 0.30 * (pago == "efectivo")
    )
    churn = (rng.random(n) < _sigmoide(logit)).astype(int)

    return pd.DataFrame({
        "id_cliente": [f"C{4200000 + i}" for i in range(n)],
        "antiguedad_meses": antiguedad,
        "tipo_plan": plan,
        "cargo_mensual": cargo,
        "reclamos_ult_3m": reclamos,
        "uso_datos_gb": uso,
        "metodo_pago": pago,
        "renovo_contrato": renovo,
        "rango_edad": edad,
        "churn": churn,
    })[COLUMNAS]


def aplicar_crisis(df: pd.DataFrame) -> pd.DataFrame:
    """Copia de df con cargos +30 % y reclamos x2 (T106, FR-014; D6); no toca otras columnas."""
    out = df.copy()
    out["cargo_mensual"] = np.clip((out["cargo_mensual"] * 1.3).round(2), *CARGO)
    out["reclamos_ult_3m"] = np.clip(out["reclamos_ult_3m"] * 2, *RECLAMOS).astype(int)
    return out


def validar(df: pd.DataFrame) -> None:
    """Falla con mensaje claro si el esquema, los nulos, los dominios o los duplicados no cumplen."""
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"faltan columnas: {faltan}")
    if df[COLUMNAS].isna().any().any():
        raise ValueError("el dataset contiene nulos")
    if df["id_cliente"].duplicated().any():
        raise ValueError("id_cliente duplicado")
    dominios = {
        "tipo_plan": config.PLANES, "metodo_pago": config.METODOS_PAGO,
        "renovo_contrato": config.RENOVACION, "rango_edad": config.RANGOS_EDAD,
        "churn": [0, 1],
    }
    for col, validos in dominios.items():
        fuera = set(df[col].unique()) - set(validos)
        if fuera:
            raise ValueError(f"{col}: valores fuera de dominio {sorted(map(str, fuera))}")
    rangos = {
        "antiguedad_meses": ANTIGUEDAD, "cargo_mensual": CARGO,
        "reclamos_ult_3m": RECLAMOS, "uso_datos_gb": USO_DATOS,
    }
    for col, (lo, hi) in rangos.items():
        if not df[col].between(lo, hi).all():
            raise ValueError(f"{col}: valores fuera del rango {lo}–{hi}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera el dataset sintético de churn")
    ap.add_argument("--escenario", choices=ESCENARIOS, default="base")
    ap.add_argument("--forzar", action="store_true", help="sobrescribe el CSV existente")
    args = ap.parse_args()

    df = generar(config.N_CLIENTES, config.SEED, args.escenario)
    validar(df)
    print(f"{len(df)} filas · escenario {args.escenario} · churn {df['churn'].mean():.1%}")

    # El escenario crisis es solo para pruebas de drift: nunca toca data/raw
    if args.escenario == "base":
        if config.DATA_RAW.exists() and not args.forzar:
            print(f"{config.DATA_RAW} ya existe; use --forzar para sobrescribirlo")
        else:
            config.DATA_RAW.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(config.DATA_RAW, index=False)
            print(f"guardado en {config.DATA_RAW}")


if __name__ == "__main__":
    main()
