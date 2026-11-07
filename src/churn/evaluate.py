"""Métricas técnicas, de negocio y de equidad (T011, FR-018, SC-004, SC-010)."""
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


def metricas_equidad(y, proba, grupos, umbral: float) -> dict:
    """Tasa de selección y recall por grupo, ratio de impacto dispar y brecha máxima de recall."""
    y, grupos = np.asarray(y), np.asarray(grupos)
    pred = np.asarray(proba) >= umbral
    por_grupo = {}
    for g in sorted(set(grupos)):
        m = grupos == g
        positivos = int(y[m].sum())
        por_grupo[str(g)] = {
            "n": int(m.sum()),
            "tasa_seleccion": float(pred[m].mean()),
            # Sin positivos reales el recall no está definido: no se inventa
            "recall": float(pred[m][y[m] == 1].mean()) if positivos else None,
        }
    tasas = [v["tasa_seleccion"] for v in por_grupo.values()]
    recalls = [v["recall"] for v in por_grupo.values() if v["recall"] is not None]
    return {
        "grupos": por_grupo,
        # Regla de los 4/5: menor tasa de selección / mayor; < 0,8 indica impacto dispar
        "ratio_impacto_dispar": min(tasas) / max(tasas) if max(tasas) > 0 else None,
        "dif_max_recall": max(recalls) - min(recalls) if len(recalls) > 1 else None,
    }
