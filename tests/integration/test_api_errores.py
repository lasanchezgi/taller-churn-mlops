"""Los errores no devuelven valores de entrada ni trazas internas (T071, T080; FR-007, FR-012, FR-022)."""
import pytest
from fastapi.testclient import TestClient

from churn import predict

SENTINELA = "VALOR-SENSIBLE-9931"


def _sin_fugas(texto: str):
    for prohibido in (SENTINELA, "Traceback", ".py", "/Users", "site-packages", "joblib"):
        assert prohibido not in texto


@pytest.mark.parametrize("campo,valor", [
    ("id_cliente", SENTINELA + "!"),          # símbolo no permitido
    ("id_cliente", SENTINELA * 10),           # demasiado largo
    ("tipo_plan", SENTINELA),                 # fuera de dominio
    ("metodo_pago", SENTINELA),
    ("antiguedad_meses", SENTINELA),          # tipo incorrecto
    ("cargo_mensual", SENTINELA),
    ("campo_extra_" + SENTINELA, SENTINELA),  # campo no previsto
])
def test_422_no_repite_el_valor_recibido(client, cliente_valido, campo, valor):
    r = client.post("/predict", json={**cliente_valido, campo: valor})
    assert r.status_code == 422
    if not campo.startswith("campo_extra_"):  # el nombre del campo extra sí se nombra (FR-007)
        _sin_fugas(r.text)
    else:
        assert SENTINELA not in r.json()["detalle"][0]["mensaje"]


def test_422_json_malformado_no_repite_el_cuerpo(client):
    r = client.post("/predict", content=("{" + SENTINELA).encode(),
                    headers={"content-type": "application/json"})
    assert r.status_code == 422
    _sin_fugas(r.text)


def test_422_en_lote_no_repite_el_id(client, clientes_lote):
    clientes = clientes_lote(3)
    clientes[1]["id_cliente"] = SENTINELA + "$"
    r = client.post("/predict/lote", json={"clientes": clientes})
    assert r.status_code == 422 and r.json()["detalle"][0]["posicion_cliente"] == 2
    _sin_fugas(r.text)


@pytest.mark.parametrize("campo,valor", [("presupuesto", 0), ("presupuesto", 100_000.01),
                                         ("costo_por_contacto", 0), ("costo_por_contacto", 1000.01)])
def test_presupuesto_y_costo_fuera_de_rango_dan_mensaje_claro(client, clientes_lote, campo, valor):
    r = client.post("/campana/contactos", json={"clientes": clientes_lote(3), campo: valor})
    assert r.status_code == 422
    d = {x["campo"]: x["mensaje"] for x in r.json()["detalle"]}
    assert campo in d and ("mayor o igual" in d[campo] or "menor o igual" in d[campo])


def test_500_no_devuelve_trazas_ni_rutas(client, cliente_valido, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError(f"fallo en /Users/x/secreto.py con {SENTINELA}")
    monkeypatch.setattr(predict, "puntuar", falla)
    with TestClient(client.app, raise_server_exceptions=False) as c:
        r = c.post("/predict", json={**cliente_valido, "id_cliente": SENTINELA})
    assert r.status_code == 500 and r.json() == {"error": "Error interno"}
    _sin_fugas(r.text)


def test_503_sin_modelo_no_expone_rutas(client_sin_modelo, cliente_valido):
    for r in (client_sin_modelo.post("/predict", json=cliente_valido), client_sin_modelo.get("/health")):
        assert r.status_code == 503
        _sin_fugas(r.text)
