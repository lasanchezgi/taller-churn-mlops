"""Integridad del modelo por huella SHA-256 (T070, T079, T129; FR-021, FR-013)."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from churn import config, predict


@pytest.fixture
def copia(ruta_modelo, tmp_path):
    """Copia modificable del modelo y de su ficha."""
    d = tmp_path / "copia"
    d.mkdir()
    shutil.copy(ruta_modelo, d / "churn_model.joblib")
    shutil.copy(ruta_modelo.parent / "model_card.json", d / "model_card.json")
    return d


def test_modelo_integro_carga(copia):
    assert predict.cargar_modelo(copia / "churn_model.joblib")["card"]["version"]


def test_archivo_alterado_no_carga(copia):
    with open(copia / "churn_model.joblib", "ab") as f:
        f.write(b"\x00")
    with pytest.raises(predict.ModeloNoDisponible):
        predict.cargar_modelo(copia / "churn_model.joblib")


def test_no_deserializa_un_archivo_alterado(copia, monkeypatch):
    """La huella se verifica antes de joblib.load (pickle puede ejecutar código)."""
    (copia / "churn_model.joblib").write_bytes(b"otro contenido")
    llamado = []
    monkeypatch.setattr(predict.joblib, "load", lambda *a, **k: llamado.append(1))
    with pytest.raises(predict.ModeloNoDisponible):
        predict.cargar_modelo(copia / "churn_model.joblib")
    assert not llamado


def test_ficha_sin_huella_o_ausente_no_carga(copia):
    card = json.loads((copia / "model_card.json").read_text())
    del card["hash_modelo"]
    (copia / "model_card.json").write_text(json.dumps(card))
    with pytest.raises(predict.ModeloNoDisponible):
        predict.cargar_modelo(copia / "churn_model.joblib")
    (copia / "model_card.json").unlink()
    with pytest.raises(predict.ModeloNoDisponible):
        predict.cargar_modelo(copia / "churn_model.joblib")


def test_api_con_modelo_alterado_predict_503_y_health_no_sano(copia, cliente_valido, monkeypatch):
    with open(copia / "churn_model.joblib", "ab") as f:
        f.write(b"\x00")
    monkeypatch.setattr(config, "MODEL_PATH", copia / "churn_model.joblib")
    from churn.api import app
    with TestClient(app) as c:
        r = c.post("/predict", json=cliente_valido)
        assert r.status_code == 503 and "probabilidad_churn" not in r.json()
        h = c.get("/health")
        assert h.status_code == 503
        assert h.json()["estado"] == "no_sano" and h.json()["modelo_cargado"] is False
