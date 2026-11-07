"""Carga del modelo y puntuación de uno o varios clientes (T022, T030; FR-001..004, FR-009, FR-013)."""
from pathlib import Path

import joblib
import pandas as pd

from churn import config
from churn.recomendaciones import CATALOGO


class ModeloNoDisponible(RuntimeError):
    """El modelo no está cargado: no se devuelven predicciones (FR-013)."""


def cargar_modelo(ruta=None) -> dict:
    """Lee {"pipeline", "card"}; si falta o no es válido lanza ModeloNoDisponible."""
    ruta = ruta or config.MODEL_PATH
    try:
        modelo = joblib.load(ruta)
        modelo["pipeline"], modelo["card"]["version"]
    except Exception as e:  # archivo ausente, corrupto o con otra estructura
        raise ModeloNoDisponible(f"no se pudo cargar el modelo en {Path(ruta).name}") from e
    return modelo


def nivel_riesgo(probabilidad: float) -> str:
    """alto >= 0,70 · medio >= 0,50 y < 0,70 · bajo < 0,50 (FR-002)."""
    if probabilidad >= config.UMBRAL_RIESGO_ALTO:
        return "alto"
    if probabilidad >= config.UMBRAL_RIESGO_MEDIO:
        return "medio"
    return "bajo"


def alerta_equidad(card: dict) -> str | None:
    """Texto de alerta si el modelo no está aprobado para despliegue; None si lo está (FR-026, D2)."""
    if card.get("aprobado_para_despliegue") is True:
        return None
    return ("Alerta de equidad: modelo no aprobado para despliegue ("
            + "; ".join(razones_no_aprobado(card)) + "). Úselo solo como apoyo con revisión humana.")


def razones_no_aprobado(card: dict) -> list[str]:
    """Razones del card; si faltan, un texto genérico (nunca una lista vacía en un modelo no aprobado)."""
    if card.get("aprobado_para_despliegue") is True:
        return []
    return list(card.get("razones_no_aprobado") or ["no cumple las condiciones de aprobación"])


def puntuar(modelo: dict | None, cliente: dict) -> dict:
    """Probabilidad, nivel, recomendación y versión; solo usa config.FEATURES."""
    if modelo is None:
        raise ModeloNoDisponible("modelo no cargado")
    fila = pd.DataFrame([{c: cliente[c] for c in config.FEATURES}])
    prob = float(modelo["pipeline"].predict_proba(fila)[0, 1])
    nivel = nivel_riesgo(prob)
    return {
        "probabilidad_churn": prob,
        "nivel_riesgo": nivel,
        "recomendacion": CATALOGO[nivel],
        "version_modelo": modelo["card"]["version"],
    }


def puntuar_lote(modelo: dict | None, clientes: list[dict]) -> list[dict]:
    """Una sola llamada vectorizada; conserva el orden de entrada (FR-009)."""
    if modelo is None:
        raise ModeloNoDisponible("modelo no cargado")
    filas = pd.DataFrame([{c: cl[c] for c in config.FEATURES} for cl in clientes])
    probas = modelo["pipeline"].predict_proba(filas)[:, 1]
    version = modelo["card"]["version"]
    salida = []
    for p in probas:
        nivel = nivel_riesgo(float(p))
        salida.append({"probabilidad_churn": float(p), "nivel_riesgo": nivel,
                       "recomendacion": CATALOGO[nivel], "version_modelo": version})
    return salida
