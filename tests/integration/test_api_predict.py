"""Pruebas de POST /predict (T020; FR-001..005, FR-013, FR-022, SC-001)."""
import pytest
from fastapi.testclient import TestClient

from churn import config, predict


def test_no_devuelve_id_cliente_aunque_se_envie(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "id_cliente": "C-123"})
    assert r.status_code == 200
    assert "id_cliente" not in r.json() and "C-123" not in r.text


def test_misma_entrada_misma_salida(client, cliente_valido):
    a = client.post("/predict", json=cliente_valido).json()
    assert a == client.post("/predict", json=cliente_valido).json()


@pytest.mark.parametrize("p,nivel", [(0.70, "alto"), (0.699, "medio"), (0.50, "medio"),
                                     (0.499, "bajo"), (0.0, "bajo"), (1.0, "alto")])
def test_nivel_de_riesgo_en_los_limites(p, nivel):
    assert predict.nivel_riesgo(p) == nivel


def test_sin_modelo_responde_503_sin_prediccion(client_sin_modelo, cliente_valido):
    r = client_sin_modelo.post("/predict", json=cliente_valido)
    assert r.status_code == 503
    assert r.json() == {"error": "Modelo no disponible"}


def test_error_interno_responde_500_generico(ruta_modelo, cliente_valido, monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", ruta_modelo)
    from churn.api import app

    def falla(*a, **k):
        raise RuntimeError("secreto /ruta/interna/archivo.py")

    monkeypatch.setattr(predict, "puntuar", falla)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/predict", json=cliente_valido)
    assert r.status_code == 500
    assert r.json() == {"error": "Error interno"}
    assert "secreto" not in r.text and "Traceback" not in r.text
