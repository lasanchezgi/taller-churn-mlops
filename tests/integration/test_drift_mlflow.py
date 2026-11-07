"""drift --mlflow (T141; FR-031, SC-011; D11)."""
import pytest

from churn import config, drift
from churn.features import cargar_datos
from churn.predict import cargar_modelo
from churn.train import entrenar, guardar_modelo

mlflow = pytest.importorskip("mlflow")


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    res = entrenar(cargar_datos(config.DATA_RAW), "logreg")
    guardar_modelo(res, tmp_path / "m.joblib", tmp_path / "card.json")
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "m.joblib")
    monkeypatch.setattr(config, "MODEL_CARD_PATH", tmp_path / "card.json")
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    monkeypatch.setattr(config, "MLFLOW_ARTIFACTS_DIR", tmp_path / "mlruns")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_sin_la_opcion_no_se_crea_nada(entorno):
    drift.main(["--escenario", "crisis"])
    assert not (entorno / "mlflow.db").exists()


def test_con_la_opcion_deja_una_corrida_con_el_psi_de_cada_variable(entorno):
    drift.main(["--escenario", "crisis", "--mlflow"])
    client = mlflow.MlflowClient(config.MLFLOW_TRACKING_URI)
    exp = client.get_experiment_by_name("churn-drift")
    runs = client.search_runs([exp.experiment_id])
    assert len(runs) == 1
    m = runs[0].data.metrics
    for v in config.FEATURES:
        assert f"psi_{v}" in m, v
    assert m["psi_reclamos_ult_3m"] >= config.PSI_CRITICO
    assert runs[0].data.params["escenario"] == "crisis"
    assert runs[0].data.tags["estado_general"] == "critico"
    assert "drift.json" in {a.path for a in client.list_artifacts(runs[0].info.run_id)}
