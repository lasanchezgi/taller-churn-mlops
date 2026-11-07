"""Entrenamiento del modelo de churn (T015, T119, T121; FR-016, FR-018, FR-024, FR-027, SC-004, SC-010).

Uso: python -m churn.train [--algoritmo logreg|rf] [--mlflow]

--mlflow registra la corrida en el seguimiento local opcional (T143, FR-029, FR-030; D11).
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from churn import config
from churn.evaluate import (
    metricas_equidad, metricas_negocio, metricas_tecnicas, precision_en_top, roi_estimado,
)
from churn.features import (
    cargar_datos, construir_preprocesador, particionar, validar_calidad,
)

ALGORITMOS = ("logreg", "rf")
# Variables que podrían sustituir a la edad (FR-024)
PROXIES_EDAD = ("metodo_pago", "tipo_plan", "antiguedad_meses")


def construir_modelo(algoritmo: str = "logreg", excluir: tuple = ()) -> Pipeline:
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
    return Pipeline([("prep", construir_preprocesador(excluir)), ("clf", clf)])


def elegir_umbral(y, proba) -> tuple[float, str]:
    """Regla de FR-027 (D4): mayor precision con recall >= MIN_RECALL; si ninguno, el de mayor recall.

    Nunca lanza error: el modelo siempre se guarda y los criterios dicen si queda aprobado.
    """
    precision, recall, umbrales = precision_recall_curve(y, proba)
    p, r = precision[:-1], recall[:-1]
    ok = r >= config.MIN_RECALL
    if ok.any():
        # Entre los que cumplen el recall, el de mayor precision (empate: el umbral más alto)
        idx = np.flatnonzero(ok)
        return float(umbrales[idx[np.lexsort((umbrales[idx], p[idx]))[-1]]]), "mayor_precision_con_recall"
    idx = np.flatnonzero(r == r.max())  # mayor recall; entre empates, el umbral más alto
    return float(umbrales[idx[np.argmax(umbrales[idx])]]), "mayor_recall"


def calibrar_umbral(pipe: Pipeline, X, y) -> tuple[float, str]:
    """Umbral y regla aplicada, con probabilidades fuera de muestra (validación cruzada sobre train)."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=config.SEED)
    proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    return elegir_umbral(y, proba)


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


def guardar_modelo(res: dict, ruta_modelo, ruta_card) -> dict:
    """Guarda el .joblib y el model card con `hash_modelo` (SHA-256 del .joblib; T129, FR-021).

    La huella solo va en el JSON: el .joblib contiene el card y no puede llevar su propio hash.
    """
    ruta_modelo, ruta_card = Path(ruta_modelo), Path(ruta_card)
    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": res["pipeline"], "card": res["card"]}, ruta_modelo)
    card = {**res["card"], "hash_modelo": hash_archivo(ruta_modelo)}
    ruta_card.parent.mkdir(parents=True, exist_ok=True)
    ruta_card.write_text(json.dumps(card, indent=2, ensure_ascii=False))
    return card


def evaluar_variante(tr, te, algoritmo: str, excluir: tuple = ()) -> dict:
    """Entrena una variante (otro algoritmo o sin ciertas features) y mide su equidad en prueba.

    Un solo umbral por modelo; rango_edad solo agrupa la auditoría (FR-024, D2).
    """
    cols = [c for c in config.FEATURES if c not in excluir]
    pipe = construir_modelo(algoritmo, excluir)
    umbral, regla = calibrar_umbral(pipe, tr[cols], tr[config.TARGET])
    pipe.fit(tr[cols], tr[config.TARGET])
    proba = pipe.predict_proba(te[cols])[:, 1]
    tec = metricas_tecnicas(te[config.TARGET], proba, umbral)
    eq = metricas_equidad(te[config.TARGET], proba, te[config.SENSITIVE_COL], umbral)
    return {"algoritmo": algoritmo, "excluye": list(excluir), "features": cols, "umbral": umbral,
            "regla_umbral": regla, "recall": tec["recall"], "precision": tec["precision"],
            "roc_auc": tec["roc_auc"], "dif_max_recall": eq["dif_max_recall"],
            "ratio_impacto_dispar": eq["ratio_impacto_dispar"],
            "recall_por_grupo": {g: v["recall"] for g, v in eq["grupos"].items()}}


def _razones(criterios: dict, tec: dict, top: dict, roi: dict, eq: dict) -> list[str]:
    """Una razón legible por cada criterio incumplido (alimenta la alerta de equidad y /health)."""
    r = []
    if not criterios["recall"]:
        r.append(f"recall {tec['recall']:.3f} < {config.MIN_RECALL}")
    if not criterios["precision"]:
        r.append(f"precision {tec['precision']:.3f} < {config.MIN_PRECISION}")
    if not criterios["precision_top"]:
        r.append(f"precision en el {config.TOP_EVALUACION:.0%} de mayor riesgo {top['precision']:.3f} < {config.MIN_PRECISION_TOP}")
    if not criterios["roc_auc"]:
        r.append(f"ROC-AUC {tec['roc_auc']:.3f} < {config.MIN_ROC_AUC}")
    if not criterios["roi"]:
        r.append(f"ROI estimado {roi['roi']:.2f} < {config.MIN_ROI}")
    if not criterios["equidad_recall"]:
        rec = {g: v["recall"] for g, v in eq["grupos"].items() if v["recall"] is not None}
        extremos = f" ({max(rec, key=rec.get)}: {max(rec.values()):.3f}; {min(rec, key=rec.get)}: {min(rec.values()):.3f})" if rec else ""
        dif = eq["dif_max_recall"]
        r.append(f"brecha de recall entre grupos de edad {'sin calcular' if dif is None else f'{dif:.3f}'} > {config.MAX_DIF_RECALL}{extremos}")
    if not criterios["ratio_impacto_dispar"]:
        ratio = eq["ratio_impacto_dispar"]
        r.append(f"ratio de impacto dispar {'sin calcular' if ratio is None else f'{ratio:.3f}'} < {config.MIN_RATIO_IMPACTO}")
    if not criterios["tamano_grupos"]:
        chicos = [g for g, v in eq["grupos"].items() if v["n"] < config.MIN_GRUPO_AUDITORIA]
        r.append(f"grupos de edad con menos de {config.MIN_GRUPO_AUDITORIA} clientes en la prueba: {chicos}")
    return r


def entrenar(df, algoritmo: str = "logreg", hash_dataset: str | None = None) -> dict:
    """Entrena con train, calibra el umbral en train y evalúa una sola vez en test."""
    validar_calidad(df)
    tr, te = particionar(df)
    X_tr, y_tr = tr[config.FEATURES], tr[config.TARGET]
    X_te, y_te = te[config.FEATURES], te[config.TARGET]

    pipe = construir_modelo(algoritmo)
    umbral, regla = calibrar_umbral(pipe, X_tr, y_tr)
    pipe.fit(X_tr, y_tr)

    proba = pipe.predict_proba(X_te)[:, 1]
    tecnicas = metricas_tecnicas(y_te, proba, umbral)
    top = precision_en_top(y_te, proba)
    roi = roi_estimado(y_te, proba, te["cargo_mensual"])
    negocio = metricas_negocio(proba, te["cargo_mensual"], umbral)
    negocio["roi_estimado"] = roi["roi"]
    negocio["roi_detalle"] = {k: roi[k] for k in ("k", "costo", "ingresos_retenidos_estimados")}
    # rango_edad solo audita: no entra al modelo
    equidad = metricas_equidad(y_te, proba, te[config.SENSITIVE_COL], umbral)

    dif, ratio = equidad["dif_max_recall"], equidad["ratio_impacto_dispar"]
    criterios = {  # los 5 de la constitución I (FR-018) y las condiciones de equidad (SC-010)
        "recall": tecnicas["recall"] >= config.MIN_RECALL,
        "precision": tecnicas["precision"] >= config.MIN_PRECISION,
        "precision_top": top["precision"] >= config.MIN_PRECISION_TOP,
        "roc_auc": tecnicas["roc_auc"] >= config.MIN_ROC_AUC,
        "roi": roi["roi"] >= config.MIN_ROI,
        "equidad_recall": dif is not None and dif <= config.MAX_DIF_RECALL,
        "ratio_impacto_dispar": ratio is not None and ratio >= config.MIN_RATIO_IMPACTO,
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
        "regla_umbral": regla,
        "metricas_test": {**tecnicas, "precision_top": top},
        "metricas_negocio": negocio,
        "equidad": equidad,
        "revision_proxies": {f"sin_{c}": evaluar_variante(tr, te, algoritmo, (c,)) for c in PROXIES_EDAD},
        "criterios_cumplidos": criterios,
        "razones_no_aprobado": _razones(criterios, tecnicas, top, roi, equidad),
        # Solo compuerta técnica; la aprobación humana (constitución VI) va en "aprobacion"
        "aprobado_para_despliegue": all(criterios.values()),
        "aprobacion": {"aprobado_por": None, "fecha": None},
        "perfil_referencia": perfil_referencia(X_tr),
    }
    return {"pipeline": pipe, "card": card, "umbral": umbral, "algoritmo": algoritmo,
            "metricas": tecnicas, "ejemplo_entrada": X_te.head(5).copy()}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Entrena el modelo de churn")
    ap.add_argument("--algoritmo", choices=ALGORITMOS, default="logreg",
                    help="rf solo si la regresión logística no cumple los criterios")
    ap.add_argument("--mlflow", action="store_true",
                    help="registrar la corrida y el modelo (candidato) en el seguimiento local; requiere el extra")
    args = ap.parse_args(argv)
    if args.mlflow:
        from churn import seguimiento
        seguimiento.importar_mlflow()  # falla pronto, antes de entrenar, si falta el extra

    res = entrenar(cargar_datos(config.DATA_RAW), args.algoritmo, hash_archivo(config.DATA_RAW))
    card = res["card"]

    card = guardar_modelo(res, config.MODEL_PATH, config.MODEL_CARD_PATH)

    metricas = {k: card[k] for k in ("algoritmo", "umbral", "regla_umbral", "metricas_test", "metricas_negocio",
                                     "equidad", "criterios_cumplidos", "razones_no_aprobado")}
    config.METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.METRICS_PATH.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))

    m = card["metricas_test"]
    print(f"{args.algoritmo} · umbral {card['umbral']:.3f} · recall {m['recall']:.3f} · "
          f"precision {m['precision']:.3f} · ROC-AUC {m['roc_auc']:.3f}")
    print("criterios:", card["criterios_cumplidos"])
    print("aprobado_para_despliegue =", card["aprobado_para_despliegue"])
    for razon in card["razones_no_aprobado"]:
        print("  no aprobado:", razon)
    if args.mlflow:
        print("seguimiento: corrida", seguimiento.registrar_entrenamiento(res, card),
              "· modelo 'churn-retencion' con alias 'candidato'")


if __name__ == "__main__":
    main()
