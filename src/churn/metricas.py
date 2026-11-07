"""Métricas operativas y de negocio en memoria, sin identificadores (T058; FR-019, FR-023).

Solo se conservan probabilidad, nivel, cargo mensual y latencia de las últimas
predicciones del proceso; nada se escribe a disco ni se asocia a un cliente.
"""
from collections import Counter, deque
from threading import Lock

import numpy as np

from churn import config

VENTANA = 1000  # últimas predicciones usadas para latencia y negocio


class Metricas:
    def __init__(self, ventana: int = VENTANA):
        self._recientes = deque(maxlen=ventana)  # (probabilidad, nivel, cargo, latencia_ms)
        self._niveles = Counter()
        self._predicciones = 0
        self._errores = 0
        self._lock = Lock()

    def registrar_prediccion(self, probabilidad: float, nivel: str, cargo_mensual: float,
                             latencia_ms: float) -> None:
        with self._lock:
            self._predicciones += 1
            self._niveles[nivel] += 1
            self._recientes.append((probabilidad, nivel, cargo_mensual, latencia_ms))

    def registrar_error(self) -> None:
        with self._lock:
            self._errores += 1

    def resumen(self, card: dict | None) -> dict:
        with self._lock:
            recientes, niveles = list(self._recientes), dict(self._niveles)
            total, errores = self._predicciones, self._errores
        return {
            "predicciones_totales": total,
            "errores_totales": errores,
            "distribucion_riesgo": {n: niveles.get(n, 0) for n in ("alto", "medio", "bajo")},
            "latencia_ms": _latencia(recientes),
            "modelo": _modelo(card),
            "negocio": _negocio(recientes),
        }


def _latencia(recientes) -> dict:
    if not recientes:
        return {"p50": None, "p95": None}
    lat = [r[3] for r in recientes]
    return {"p50": round(float(np.percentile(lat, 50)), 3),
            "p95": round(float(np.percentile(lat, 95)), 3)}


def _modelo(card: dict | None) -> dict | None:
    if card is None:
        return None
    return {"version": card["version"], "umbral": card["umbral"],
            "metricas_offline": card["metricas_test"]}


def _negocio(recientes) -> dict:
    """Riesgo alto en la ventana, priorizados según presupuesto y ROI esperado.

    ROI esperado = (TASA_EXITO × Σ prob × cargo × 6 − costo) / costo. Es una estimación,
    no el ingreso incremental medido contra un grupo de control (ASUM-DM §1.2).
    """
    altos = sorted((r for r in recientes if r[1] == "alto"), key=lambda r: -r[0])
    max_contactos = int(config.PRESUPUESTO_CAMPANA // config.COSTO_CONTACTO)
    priorizados = altos[:max_contactos]
    costo = len(priorizados) * config.COSTO_CONTACTO
    ingresos_mensuales = float(sum(r[2] for r in altos))
    retenido = config.TASA_EXITO_CAMPANA * sum(r[0] * r[2] * 6 for r in priorizados)
    return {
        "predicciones_en_ventana": len(recientes),
        "clientes_en_riesgo": len(altos),
        "ingresos_mensuales_en_riesgo": round(ingresos_mensuales, 2),
        "ingresos_6_meses_en_riesgo": round(ingresos_mensuales * 6, 2),
        "clientes_priorizados": len(priorizados),
        "costo_campana": round(costo, 2),
        "roi_esperado": round((retenido - costo) / costo, 3) if costo else None,
    }
