"""Brecha de la meta de −3 pp (ASUM-DM §1.4, D10): genera la tabla con supuestos explícitos.

Uso: uv run python scripts/brecha_meta.py
Fórmula: retenidos = contactos × precision@k × tasa_exito ; baja_pp = 100 × retenidos / base
"""
import sys

import joblib
import numpy as np

from churn import config
from churn.evaluate import _top_indices
from churn.features import cargar_datos, particionar

BASE = config.N_CLIENTES


def retenidos(contactos: int, precision: float, exito: float = config.TASA_EXITO_CAMPANA) -> float:
    """Churners contactados (contactos × precision) que la campaña logra retener."""
    return contactos * precision * exito


def baja_pp(contactos: int, precision: float, exito: float = config.TASA_EXITO_CAMPANA,
            base: int = BASE) -> float:
    """Puntos porcentuales que baja la tasa de churn mensual de la base."""
    return 100 * retenidos(contactos, precision, exito) / base


def precision_a_escala(y, proba, contactos: int, base: int = BASE) -> tuple[int, float]:
    """Precision en el top con k escalado: contactos/base del conjunto de prueba."""
    k = max(1, int(len(y) * contactos / base))
    return k, float(np.asarray(y)[_top_indices(proba, k)].mean())


def main() -> None:
    _, te = particionar(cargar_datos())
    pipe = joblib.load(config.MODEL_PATH)["pipeline"]
    proba = pipe.predict_proba(te[config.FEATURES])[:, 1]
    y = te[config.TARGET].to_numpy()

    print(f"Base={BASE}  éxito={config.TASA_EXITO_CAMPANA}  costo={config.COSTO_CONTACTO}  prueba={len(y)}")
    print("contactos | k_prueba | precision@k | retenidos | baja_pp | costo")
    for c in (250, 500, 750, 800, 1000):
        k, p = precision_a_escala(y, proba, c)
        print(f"{c:9d} | {k:8d} | {p:11.3f} | {retenidos(c, p):9.1f} | {baja_pp(c, p):7.2f} | {c * config.COSTO_CONTACTO:7.0f}")

    print("\nSensibilidad a 250 contactos según la precision supuesta:")
    p_top = precision_a_escala(y, proba, 250)[1]
    p_global = float(y[proba >= joblib.load(config.MODEL_PATH)["card"]["umbral"]].mean())
    for nombre, p in (("mínima aceptada (0,40)", config.MIN_PRECISION),
                      ("global con umbral (todos los marcados)", p_global),
                      ("precision@5 % (ranking)", p_top)):
        print(f"  {nombre:42s} p={p:.3f} -> {retenidos(250, p):5.1f} retenidos, {baja_pp(250, p):.2f} pp")
    p_necesaria = 150 / (250 * config.TASA_EXITO_CAMPANA)
    print(f"\nPara -3 pp con 250 contactos haría falta precision {p_necesaria:.2f} (>1: imposible).")
    sys.exit(0)


if __name__ == "__main__":
    main()
