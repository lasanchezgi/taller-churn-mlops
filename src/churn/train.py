"""Entrenamiento del modelo de churn (T015, FR-016, FR-018, SC-004).

Uso: python -m churn.train [--algoritmo logreg|rf]
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from churn import config
from churn.evaluate import metricas_equidad, metricas_negocio, metricas_tecnicas
from churn.features import (
    cargar_datos, construir_preprocesador, particionar, validar_calidad,
)

ALGORITMOS = ("logreg", "rf")


def construir_modelo(algoritmo: str = "logreg") -> Pipeline:
    """Pipeline: preprocesador + clasificador (el preprocesamiento se ajusta solo con train)."""
    if algoritmo == "logreg":
        clf = LogisticRegression(class_weight="balanced", max_iter=1000,
                                 random_state=config.SEED)
    elif algoritmo == "rf":
        clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5,
                                     class_weight="balanced", random_state=config.SEED,
                                     n_jobs=1)
    else:
        raise ValueError(f"algoritmo '{algoritmo}' no válido; use uno de {list(ALGORITMOS)}")
    return Pipeline([("prep", construir_preprocesador()), ("clf", clf)])


def calibrar_umbral(pipe: Pipeline, X, y) -> float:
    """Umbral de mayor precisión con recall >= MIN_RECALL, con probabilidades fuera de muestra."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=config.SEED)
    proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    precision, recall, umbrales = precision_recall_curve(y, proba)
    ok = recall[:-1] >= config.MIN_RECALL
    if not ok.any():
        raise RuntimeError(f"ningún umbral alcanza recall >= {config.MIN_RECALL}")
    # Entre los que cumplen el recall, el de mayor precisión (empate: el umbral más alto)
    idx = np.flatnonzero(ok)
    mejor = idx[np.lexsort((umbrales[idx], precision[:-1][idx]))[-1]]
    return float(umbrales[mejor])


def perfil_referencia(X) -> dict:
    """Perfil para drift: deciles y proporciones por intervalo (numéricas) y por categoría."""
    perfil = {}
    for col in config.NUMERIC_FEATURES:
        # Límites internos de los deciles; se quitan repetidos (p. ej. reclamos casi discretos)
        lim = np.unique(np.quantile(X[col], np.linspace(0.1, 0.9, 9)))
        cuentas, _ = np.histogram(X[col], bins=[-np.inf, *lim, np.inf])
        perfil[col] = {"tipo": "numerica", "limites": lim.tolist(),
                       "frecuencias": (cuentas / len(X)).tolist()}
    for col in config.CATEGORICAL_FEATURES:
        perfil[col] = {"tipo": "categorica",
                       "frecuencias": X[col].value_counts(normalize=True).sort_index().to_dict()}
    return perfil


def hash_archivo(ruta) -> str:
    """SHA-256 del archivo de datos, para trazar con qué dataset se entrenó."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def entrenar(df, algoritmo: str = "logreg", hash_dataset: str | None = None) -> dict:
    """Entrena con train, calibra el umbral en train y evalúa una sola vez en test."""
    validar_calidad(df)
    tr, te = particionar(df)
    X_tr, y_tr = tr[config.FEATURES], tr[config.TARGET]
    X_te, y_te = te[config.FEATURES], te[config.TARGET]

    pipe = construir_modelo(algoritmo)
    umbral = calibrar_umbral(pipe, X_tr, y_tr)
    pipe.fit(X_tr, y_tr)

    proba = pipe.predict_proba(X_te)[:, 1]
    tecnicas = metricas_tecnicas(y_te, proba, umbral)
    negocio = metricas_negocio(proba, te["cargo_mensual"], umbral)
    # rango_edad solo audita: no entra al modelo
    equidad = metricas_equidad(y_te, proba, te[config.SENSITIVE_COL], umbral)

    dif = equidad["dif_max_recall"]
    criterios = {
        "recall": tecnicas["recall"] >= config.MIN_RECALL,
        "precision": tecnicas["precision"] >= config.MIN_PRECISION,
        "roc_auc": tecnicas["roc_auc"] >= config.MIN_ROC_AUC,
        "equidad_recall": dif is not None and dif <= config.MAX_DIF_RECALL,
        "tamano_grupos": all(g["n"] >= config.MIN_GRUPO_AUDITORIA
                             for g in equidad["grupos"].values()),
    }
    card = {
        "version": config.MODEL_VERSION,
        "algoritmo": algoritmo,
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "semilla": config.SEED,
        "hash_dataset": hash_dataset,
        "features": list(config.FEATURES),
        "umbral": umbral,
        "metricas_test": tecnicas,
        "metricas_negocio": negocio,
        "equidad": equidad,
        "criterios_cumplidos": criterios,
        # Solo compuerta técnica; la aprobación humana (constitución VI) va en "aprobacion"
        "aprobado_para_despliegue": all(criterios.values()),
        "aprobacion": {"aprobado_por": None, "fecha": None},
        "perfil_referencia": perfil_referencia(X_tr),
    }
    return {"pipeline": pipe, "card": card, "umbral": umbral, "algoritmo": algoritmo,
            "metricas": tecnicas}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Entrena el modelo de churn")
    ap.add_argument("--algoritmo", choices=ALGORITMOS, default="logreg",
                    help="rf solo si la regresión logística no cumple los criterios")
    args = ap.parse_args(argv)

    res = entrenar(cargar_datos(config.DATA_RAW), args.algoritmo, hash_archivo(config.DATA_RAW))
    card = res["card"]

    config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": res["pipeline"], "card": card}, config.MODEL_PATH)
    config.MODEL_CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.MODEL_CARD_PATH.write_text(json.dumps(card, indent=2, ensure_ascii=False))

    metricas = {k: card[k] for k in ("algoritmo", "umbral", "metricas_test", "metricas_negocio",
                                     "equidad", "criterios_cumplidos")}
    config.METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.METRICS_PATH.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))

    m = card["metricas_test"]
    print(f"{args.algoritmo} · umbral {card['umbral']:.3f} · recall {m['recall']:.3f} · "
          f"precision {m['precision']:.3f} · ROC-AUC {m['roc_auc']:.3f}")
    print("criterios:", card["criterios_cumplidos"])
    print("aprobado_para_despliegue =", card["aprobado_para_despliegue"])


if __name__ == "__main__":
    main()
