"""Seguimiento opcional de experimentos y registro de versiones (T142; FR-029, FR-030, FR-031; D11).

Todo es local (SQLite + carpeta de artefactos). `mlflow` se importa solo al usarlo: sin el extra
el resto del paquete funciona igual. Este módulo nunca asigna el alias de producción (FR-030).
"""
import json
import os

import sklearn

from churn import config


def importar_mlflow():
    """Importa mlflow o termina con instrucciones claras si el extra no está instalado."""
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    try:
        import mlflow
        import mlflow.sklearn  # noqa: F401
    except ImportError:
        raise SystemExit("--mlflow requiere el extra opcional: uv sync --extra mlflow") from None
    return mlflow


def ejemplo_entrada(df, n: int = 5):
    """Primeras filas solo con las features del modelo: sin id_cliente ni rango_edad (FR-029)."""
    return df[config.FEATURES].head(n).copy()


def _preparar(mlflow, experimento: str):
    """Fija la URI local y crea el experimento con sus artefactos en ./mlruns si no existe."""
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    if mlflow.get_experiment_by_name(experimento) is None:
        config.MLFLOW_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        mlflow.create_experiment(experimento, artifact_location=config.MLFLOW_ARTIFACTS_DIR.as_uri())
    mlflow.set_experiment(experimento)


def _numeros(d: dict) -> dict:
    """Solo valores numéricos reales (se omiten None y anidados)."""
    return {k: float(v) for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def metricas_del_card(card: dict) -> dict:
    """Métricas técnicas, de negocio y de equidad del model card, con nombres planos."""
    tec, neg, eq = card["metricas_test"], card["metricas_negocio"], card["equidad"]
    return {
        **_numeros({k: tec[k] for k in ("roc_auc", "precision", "recall", "f1")}),
        **_numeros({k: neg[k] for k in ("clientes_en_riesgo", "ingresos_mensuales_en_riesgo",
                                         "ingresos_6_meses_en_riesgo", "clientes_priorizados",
                                         "costo_campana", "roi_estimado")}),
        "precision_top_5pct": float(tec["precision_top"]["precision"]),
        **_numeros({k: eq[k] for k in ("dif_max_recall", "ratio_impacto_dispar")}),
    }


def registrar_entrenamiento(res: dict, card: dict) -> str:
    """Una corrida por entrenamiento + versión «candidata» en el registro. `card` es el guardado (con hash)."""
    mlflow = importar_mlflow()
    from mlflow.models import infer_signature
    _preparar(mlflow, config.MLFLOW_EXPERIMENTO_ENTRENAMIENTO)
    pipe, ejemplo = res["pipeline"], res["ejemplo_entrada"]
    clf_params = {k: str(v) for k, v in pipe.named_steps["clf"].get_params().items()}

    with mlflow.start_run(run_name=f"{card['algoritmo']}-{card['version']}") as run:
        mlflow.log_params({"algoritmo": card["algoritmo"], "semilla": card["semilla"],
                           "umbral": card["umbral"], "regla_umbral": card["regla_umbral"],
                           **{f"clf_{k}": v for k, v in clf_params.items()}})
        mlflow.log_metrics(metricas_del_card(card))
        mlflow.set_tags({"version_modelo": card["version"], "hash_dataset": str(card["hash_dataset"]),
                         "aprobado_para_despliegue": str(card["aprobado_para_despliegue"]).lower(),
                         "criterios_cumplidos": json.dumps(card["criterios_cumplidos"])})
        mlflow.log_dict(card, "model_card.json")
        mlflow.log_dict(card["metricas_test"]["matriz_confusion"], "matriz_confusion.json")
        mlflow.log_dict(card["equidad"], "reporte_equidad.json")
        info = mlflow.sklearn.log_model(
            pipe, name="modelo", registered_model_name=config.MLFLOW_MODELO_REGISTRADO,
            signature=infer_signature(ejemplo, pipe.predict(ejemplo)), input_example=ejemplo,
            serialization_format="cloudpickle",  # skops no admite los árboles del Random Forest
            pip_requirements=[f"scikit-learn=={sklearn.__version__}", "pandas", "numpy"])

    client = mlflow.MlflowClient()
    version = info.registered_model_version
    nombre = config.MLFLOW_MODELO_REGISTRADO
    # Solo «candidato»: «produccion» lo asigna scripts/promover_modelo.py (FR-030)
    client.set_registered_model_alias(nombre, config.ALIAS_CANDIDATO, version)
    for k, v in (("aprobado_para_despliegue", str(card["aprobado_para_despliegue"]).lower()),
                 ("hash_modelo", str(card.get("hash_modelo")))):
        client.set_model_version_tag(nombre, version, k, v)
    return run.info.run_id


def registrar_drift(reporte: dict) -> str:
    """Una corrida en «churn-drift»: PSI por variable como métricas y el informe como artefacto (FR-031)."""
    mlflow = importar_mlflow()
    _preparar(mlflow, config.MLFLOW_EXPERIMENTO_DRIFT)
    sim = reporte.get("simulacion", {})
    with mlflow.start_run(run_name=f"drift-{sim.get('escenario', 'lote')}") as run:
        mlflow.log_params({"escenario": sim.get("escenario", "lote"),
                           "version_modelo": sim.get("version_modelo", ""), "filas": sim.get("filas", "")})
        mlflow.log_metrics({f"psi_{v['nombre']}": v["psi"] for v in reporte["variables"]})
        mlflow.set_tag("estado_general", reporte["estado_general"])
        mlflow.log_dict(reporte, "drift.json")
    return run.info.run_id
