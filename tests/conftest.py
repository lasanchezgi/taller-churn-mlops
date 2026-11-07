"""Fixtures compartidas (T016): modelo pequeño en carpeta temporal y cliente de prueba."""
import pytest
from fastapi.testclient import TestClient

from churn import config
from churn.dataset import generar
from churn.train import entrenar, guardar_modelo


@pytest.fixture
def cliente_valido():
    return {
        "antiguedad_meses": 12, "tipo_plan": "prepago", "cargo_mensual": 35.5,
        "reclamos_ult_3m": 2, "uso_datos_gb": 8.5, "metodo_pago": "efectivo",
        "renovo_contrato": "no",
    }


@pytest.fixture
def cliente_riesgoso(cliente_valido):
    """Prepago, con reclamos, sin renovar y poca antigüedad."""
    return {**cliente_valido, "tipo_plan": "prepago", "reclamos_ult_3m": 4,
            "renovo_contrato": "no", "antiguedad_meses": 3}


@pytest.fixture
def cliente_fiel(cliente_valido):
    """Pospago premium, sin reclamos, renovó y mucha antigüedad."""
    return {**cliente_valido, "tipo_plan": "pospago_premium", "reclamos_ult_3m": 0,
            "renovo_contrato": "si", "antiguedad_meses": 100, "metodo_pago": "tarjeta_credito"}


@pytest.fixture(scope="session")
def ruta_modelo(tmp_path_factory):
    res = entrenar(generar(1500), "logreg")
    ruta = tmp_path_factory.mktemp("modelo") / "churn_model.joblib"
    guardar_modelo(res, ruta, ruta.parent / "model_card.json")  # con hash_modelo (FR-021)
    return ruta


@pytest.fixture(autouse=True)
def _reportes_en_tmp(tmp_path, monkeypatch):
    """Ningún test escribe en reports/ ni en logs/ reales."""
    monkeypatch.setattr(config, "ULTIMO_LOTE_PATH", tmp_path / "ultimo_lote.json", raising=False)
    monkeypatch.setattr(config, "DRIFT_REPORT_PATH", tmp_path / "drift.json")
    monkeypatch.setattr(config, "PREDICTIONS_LOG", tmp_path / "logs" / "predicciones.jsonl")


@pytest.fixture
def clientes_lote():
    """Fábrica de lotes de clientes válidos (dicts) tomados del generador."""
    def _f(n, seed=config.SEED + 9, con_id=False):
        cols = [config.ID_COL, *config.FEATURES] if con_id else list(config.FEATURES)
        return generar(n, seed=seed)[cols].to_dict(orient="records")
    return _f


@pytest.fixture
def client(ruta_modelo, monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", ruta_modelo)
    from churn.api import app  # import diferido: toma la ruta ya redirigida
    with TestClient(app) as c:  # "with" ejecuta el lifespan
        yield c


@pytest.fixture
def client_sin_modelo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "no_existe.joblib")
    from churn.api import app
    with TestClient(app) as c:
        yield c
