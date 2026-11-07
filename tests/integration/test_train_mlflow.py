"""train --mlflow (T138; FR-029, FR-030, SC-011; D11)."""
import json
import sys
from pathlib import Path

import pytest

from churn import config, train
from churn.dataset import generar

mlflow = pytest.importorskip("mlflow")


def _configurar(tmp_path, mp):
    csv = tmp_path / "d.csv"
    generar(1500).to_csv(csv, index=False)
    mp.setattr(config, "DATA_RAW", csv)
    mp.setattr(config, "MODEL_PATH", tmp_path / "m" / "modelo.joblib")
    mp.setattr(config, "MODEL_CARD_PATH", tmp_path / "m" / "model_card.json")
    mp.setattr(config, "METRICS_PATH", tmp_path / "r" / "evaluacion.json")
    mp.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    mp.setattr(config, "MLFLOW_ARTIFACTS_DIR", tmp_path / "mlruns")


def test_sin_la_opcion_no_se_crea_nada_de_seguimiento(tmp_path, monkeypatch):
    _configurar(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    train.main([])
    assert not (tmp_path / "mlflow.db").exists() and not (tmp_path / "mlruns").exists()


@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("seg")
    with pytest.MonkeyPatch.context() as mp:
        _configurar(tmp, mp)
        train.main(["--mlflow"])
        client = mlflow.MlflowClient(config.MLFLOW_TRACKING_URI)
        exp = client.get_experiment_by_name("churn-retencion")
        runs = client.search_runs([exp.experiment_id])
        card = json.loads(config.MODEL_CARD_PATH.read_text())
        yield client, runs, card


def test_hay_una_corrida_con_parametros(corrida):
    _, runs, card = corrida
    assert len(runs) == 1
    p = runs[0].data.params
    assert p["algoritmo"] == "logreg" and p["semilla"] == str(config.SEED)
    assert float(p["umbral"]) == pytest.approx(card["umbral"]) and p["regla_umbral"] == card["regla_umbral"]


def test_trae_metricas_tecnicas_de_negocio_y_equidad(corrida):
    _, runs, card = corrida
    m = runs[0].data.metrics
    for k in ("roc_auc", "precision", "recall", "f1", "clientes_en_riesgo", "ingresos_mensuales_en_riesgo",
              "ingresos_6_meses_en_riesgo", "clientes_priorizados", "precision_top_5pct",
              "dif_max_recall", "ratio_impacto_dispar"):
        assert k in m, k
    assert m["recall"] == pytest.approx(card["metricas_test"]["recall"])
    assert m["precision_top_5pct"] == pytest.approx(card["metricas_test"]["precision_top"]["precision"])


def test_etiquetas_de_aprobacion_version_y_dataset(corrida):
    _, runs, card = corrida
    t = runs[0].data.tags
    assert t["aprobado_para_despliegue"] == str(card["aprobado_para_despliegue"]).lower()
    assert t["version_modelo"] == card["version"] and t["hash_dataset"] == card["hash_dataset"]
    assert json.loads(t["criterios_cumplidos"]) == card["criterios_cumplidos"]


def test_artefactos_y_ejemplo_de_entrada_sin_id_ni_edad(corrida, tmp_path):
    client, runs, _ = corrida
    nombres = {a.path for a in client.list_artifacts(runs[0].info.run_id)}
    assert {"model_card.json", "matriz_confusion.json", "reporte_equidad.json"} <= nombres
    modelo = mlflow.models.get_model_info(f"models:/{config.MLFLOW_MODELO_REGISTRADO}@candidato")
    assert [c.name for c in modelo.signature.inputs] == config.FEATURES
    carpeta = mlflow.artifacts.download_artifacts(
        artifact_uri=f"models:/{config.MLFLOW_MODELO_REGISTRADO}@candidato", dst_path=str(tmp_path))
    ejemplo = json.loads((Path(carpeta) / "input_example.json").read_text())
    assert ejemplo["columns"] == config.FEATURES
    assert config.ID_COL not in json.dumps(ejemplo) and config.SENSITIVE_COL not in json.dumps(ejemplo)


def test_el_modelo_queda_candidato_y_nunca_en_produccion(corrida):
    client, _, _ = corrida
    v = client.get_model_version_by_alias(config.MLFLOW_MODELO_REGISTRADO, "candidato")
    assert v.aliases == ["candidato"]
    with pytest.raises(Exception):
        client.get_model_version_by_alias(config.MLFLOW_MODELO_REGISTRADO, "produccion")


def test_sin_el_extra_la_opcion_falla_con_mensaje_claro(tmp_path, monkeypatch):
    _configurar(tmp_path, monkeypatch)
    monkeypatch.setitem(sys.modules, "mlflow", None)
    with pytest.raises(SystemExit) as e:
        train.main(["--mlflow"])
    assert "uv sync --extra mlflow" in str(e.value)


def test_tambien_se_registra_el_random_forest(tmp_path, monkeypatch):
    # El formato por defecto de MLflow (skops) rechaza los árboles: este caso lo cubre
    from churn import seguimiento
    _configurar(tmp_path, monkeypatch)
    res = train.entrenar(generar(600), "rf")
    seguimiento.registrar_entrenamiento(res, res["card"])
    v = mlflow.MlflowClient(config.MLFLOW_TRACKING_URI).get_model_version_by_alias(
        config.MLFLOW_MODELO_REGISTRADO, "candidato")
    assert v.tags["aprobado_para_despliegue"] == str(res["card"]["aprobado_para_despliegue"]).lower()
