"""Intento único de mitigación de equidad (T123; FR-024, SC-010; D2).

Compara el modelo base con (a) el modelo sin cada variable que podría sustituir a la edad y
(b) un Random Forest, y mide qué tan asociada está cada variable con la edad. La edad solo agrupa
la auditoría: nunca es predictor ni fija umbrales por grupo. No cambia el modelo servido; si ninguna
variante baja la brecha del máximo, se documenta y no se fuerza.

Uso: python -m churn.mitigacion  →  reports/metrics/mitigacion_equidad.json
"""
import json

import numpy as np
import pandas as pd

from churn import config
from churn.features import cargar_datos, particionar
from churn.train import PROXIES_EDAD, evaluar_variante


def cramers_v(a, b) -> float:
    """Asociación entre dos variables categóricas, de 0 (ninguna) a 1 (total)."""
    tabla = pd.crosstab(np.asarray(a), np.asarray(b)).to_numpy(dtype=float)
    n = tabla.sum()
    if min(tabla.shape) < 2 or n == 0:
        return 0.0
    esperado = tabla.sum(1, keepdims=True) @ tabla.sum(0, keepdims=True) / n
    chi2 = ((tabla - esperado) ** 2 / esperado).sum()
    return float(np.sqrt(chi2 / (n * (min(tabla.shape) - 1))))


def asociacion_con_edad(df: pd.DataFrame) -> dict:
    """Cramér's V entre cada feature (las numéricas en cuartiles) y rango_edad."""
    out = {}
    for col in config.FEATURES:
        x = df[col]
        if col in config.NUMERIC_FEATURES:
            x = pd.qcut(x, q=4, duplicates="drop")
        out[col] = cramers_v(x.astype(str), df[config.SENSITIVE_COL])
    return out


def ejecutar(df: pd.DataFrame | None = None) -> dict:
    """Entrena las variantes sobre el mismo split y devuelve el reporte."""
    df = cargar_datos(config.DATA_RAW) if df is None else df
    tr, te = particionar(df)
    variantes = [{"nombre": "base_logreg", **evaluar_variante(tr, te, "logreg")}]
    variantes += [{"nombre": f"sin_{c}", **evaluar_variante(tr, te, "logreg", (c,))} for c in PROXIES_EDAD]
    variantes.append({"nombre": "rf", **evaluar_variante(tr, te, "rf")})

    cumplen = [v["nombre"] for v in variantes
               if v["dif_max_recall"] is not None and v["dif_max_recall"] <= config.MAX_DIF_RECALL]
    if cumplen:
        conclusion = (f"Variantes con brecha de recall <= {config.MAX_DIF_RECALL}: {cumplen}. "
                      "No se adoptan automáticamente: requieren revisión del dueño del modelo.")
    else:
        conclusion = (f"Ninguna variante baja la brecha de recall de {config.MAX_DIF_RECALL}: "
                      "se documenta y no se fuerza.")
    grupos = {g: {"n": int((te[config.SENSITIVE_COL] == g).sum()),
                  "positivos": int(te.loc[te[config.SENSITIVE_COL] == g, config.TARGET].sum())}
              for g in config.RANGOS_EDAD}
    return {"variantes": variantes, "asociacion_con_edad": asociacion_con_edad(tr),
            "grupos": grupos, "alguna_variante_cumple": bool(cumplen), "conclusion": conclusion}


def main(argv=None) -> None:
    r = ejecutar()
    config.MITIGACION_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.MITIGACION_PATH.write_text(json.dumps(r, indent=2, ensure_ascii=False))
    print(f"{'variante':<22}{'recall':>8}{'brecha':>8}{'ratio':>8}")
    for v in r["variantes"]:
        print(f"{v['nombre']:<22}{v['recall']:>8.3f}{v['dif_max_recall']:>8.3f}{v['ratio_impacto_dispar']:>8.3f}")
    print("asociación con la edad (Cramér's V):",
          {k: round(x, 3) for k, x in r["asociacion_con_edad"].items()})
    print("grupos (n, positivos):", {g: (v["n"], v["positivos"]) for g, v in r["grupos"].items()})
    print(r["conclusion"])


if __name__ == "__main__":
    main()
