"""Métricas técnicas, de negocio y de equidad (T011, T117; FR-018, SC-004, SC-010)."""
import numpy as np
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)

from churn import config


def metricas_tecnicas(y, proba, umbral: float) -> dict:
    """ROC-AUC, precision, recall, F1 y matriz de confusión con el umbral dado."""
    y, proba = np.asarray(y), np.asarray(proba)
    pred = proba >= umbral
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, proba)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "matriz_confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def _tamano_top(n: int, fraccion: float) -> int:
    """k = fracción del conjunto evaluado (5 % → 62 de 1.250, 250 de 5.000)."""
    return max(1, int(n * fraccion))


def _top_indices(proba, k: int) -> np.ndarray:
    """Los k de mayor probabilidad; el empate respeta el orden de entrada."""
    return np.argsort(-np.asarray(proba, dtype=float), kind="stable")[:k]


def precision_en_top(y, proba, fraccion: float = config.TOP_EVALUACION) -> dict:
    """Precision entre el k = fracción del conjunto de mayor probabilidad (calidad del ranking, D-10)."""
    y = np.asarray(y)
    k = _tamano_top(len(y), fraccion)
    return {"k": k, "precision": float(y[_top_indices(proba, k)].mean())}


def roi_estimado(y, proba, cargo, fraccion: float = config.TOP_EVALUACION,
                 tasa_exito: float = config.TASA_EXITO_CAMPANA,
                 costo: float = config.COSTO_CONTACTO) -> dict:
    """ROI offline: (éxito × Σ cargo × 6 de los churners reales entre los k − k × costo) / (k × costo).

    Estimación del ASUM-DM §1.3; el ROI incremental real se mide en producción con grupo de control.
    """
    y, cargo = np.asarray(y), np.asarray(cargo, dtype=float)
    k = _tamano_top(len(y), fraccion)
    top = _top_indices(proba, k)
    retenido = tasa_exito * float(cargo[top][y[top] == 1].sum()) * 6
    gasto = k * costo
    return {"k": k, "costo": gasto, "ingresos_retenidos_estimados": retenido,
            "roi": (retenido - gasto) / gasto}


def metricas_negocio(proba, cargo, umbral: float,
                     presupuesto: float = config.PRESUPUESTO_CAMPANA,
                     costo: float = config.COSTO_CONTACTO) -> dict:
    """Clientes e ingresos en riesgo y clientes priorizados según el presupuesto."""
    en_riesgo = np.asarray(proba) >= umbral
    n_riesgo = int(en_riesgo.sum())
    ingresos = float(np.asarray(cargo, dtype=float)[en_riesgo].sum())
    max_contactos = int(presupuesto // costo)
    priorizados = min(n_riesgo, max_contactos)
    return {
        "clientes_en_riesgo": n_riesgo,
        "ingresos_mensuales_en_riesgo": ingresos,
        "ingresos_6_meses_en_riesgo": ingresos * 6,  # valor de un cliente retenido = cargo × 6
        "max_contactos": max_contactos,
        "clientes_priorizados": priorizados,
        "costo_campana": priorizados * costo,
    }


def metricas_equidad(y, proba, grupos, umbral: float, fraccion_top: float = config.TOP_EVALUACION) -> dict:
    """Por grupo: tamaño, selección, recall, precision y reparto del top; ratio de impacto dispar y brecha de recall."""
    y, grupos, proba = np.asarray(y), np.asarray(grupos), np.asarray(proba)
    pred = proba >= umbral
    top = _top_indices(proba, _tamano_top(len(y), fraccion_top))
    por_grupo = {}
    for g in sorted(set(grupos)):
        m = grupos == g
        positivos = int(y[m].sum())
        seleccionados = int(pred[m].sum())
        por_grupo[str(g)] = {
            "n": int(m.sum()),
            "peso": float(m.mean()),
            "tasa_seleccion": float(pred[m].mean()),
            # Sin positivos reales el recall no está definido: no se inventa
            "recall": float(pred[m][y[m] == 1].mean()) if positivos else None,
            "precision": float(y[m][pred[m]].mean()) if seleccionados else None,
            "reparto_top": float((grupos[top] == g).mean()),
        }
    tasas = [v["tasa_seleccion"] for v in por_grupo.values()]
    recalls = [v["recall"] for v in por_grupo.values() if v["recall"] is not None]
    return {
        "grupos": por_grupo,
        # Regla de los 4/5: menor tasa de selección / mayor; < MIN_RATIO_IMPACTO indica impacto dispar
        "ratio_impacto_dispar": min(tasas) / max(tasas) if max(tasas) > 0 else None,
        "dif_max_recall": max(recalls) - min(recalls) if len(recalls) > 1 else None,
    }
