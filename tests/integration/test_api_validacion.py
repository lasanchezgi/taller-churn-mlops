"""Validación de entrada de POST /predict (T025; FR-006..008, FR-022, SC-002, SC-006).

Los casos de campo extra `cedula`, plan inválido, campo faltante y cargo negativo viven en tests/test_api.py.
"""
import pytest


def _detalle(r):
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["error"] == "Entrada inválida"
    return {d["campo"]: d["mensaje"] for d in cuerpo["detalle"]}


def test_antiguedad_fuera_de_rango_nombra_campo_y_limite(client, cliente_valido):
    d = _detalle(client.post("/predict", json={**cliente_valido, "antiguedad_meses": 121}))
    assert "120" in d["antiguedad_meses"]


@pytest.mark.parametrize("campo,valor", [
    ("antiguedad_meses", 0), ("antiguedad_meses", 121), ("reclamos_ult_3m", -1),
    ("reclamos_ult_3m", 7), ("cargo_mensual", 9.99), ("cargo_mensual", 1000.01),
    ("uso_datos_gb", -0.1), ("uso_datos_gb", 1000.1),
])
def test_rechaza_valores_fuera_de_rango(client, cliente_valido, campo, valor):
    assert campo in _detalle(client.post("/predict", json={**cliente_valido, campo: valor}))


@pytest.mark.parametrize("campo,valor", [("antiguedad_meses", 12), ("reclamos_ult_3m", 6),
                                         ("cargo_mensual", 10), ("cargo_mensual", 1000),
                                         ("uso_datos_gb", 0), ("uso_datos_gb", 1000)])
def test_acepta_los_limites(client, cliente_valido, campo, valor):
    assert client.post("/predict", json={**cliente_valido, campo: valor}).status_code == 200


@pytest.mark.parametrize("campo,valor", [("antiguedad_meses", 12.5), ("antiguedad_meses", "12"),
                                         ("reclamos_ult_3m", 1.5), ("cargo_mensual", "alto"),
                                         ("antiguedad_meses", None), ("antiguedad_meses", True)])
def test_rechaza_tipos_incorrectos_y_decimales(client, cliente_valido, campo, valor):
    assert campo in _detalle(client.post("/predict", json={**cliente_valido, campo: valor}))


def test_rango_edad_se_rechaza_como_no_previsto(client, cliente_valido):
    d = _detalle(client.post("/predict", json={**cliente_valido, "rango_edad": "60+"}))
    assert d["rango_edad"] == "campo no previsto"


def test_id_cliente_con_caracteres_invalidos_no_se_repite(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "id_cliente": "C 1;DROP"})
    assert "id_cliente" in _detalle(r)
    assert "DROP" not in r.text


def test_id_cliente_demasiado_largo(client, cliente_valido):
    assert "id_cliente" in _detalle(client.post("/predict", json={**cliente_valido, "id_cliente": "a" * 65}))


def test_cuerpo_que_no_es_json(client):
    r = client.post("/predict", content="no es json", headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"] == "Entrada inválida"


def test_errores_no_incluyen_trazas_ni_rutas(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "antiguedad_meses": "x", "extra": 1})
    assert "Traceback" not in r.text and ".py" not in r.text
