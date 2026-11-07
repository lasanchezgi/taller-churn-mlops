"""El registro de predicciones no guarda identificadores en claro (T044, T047; FR-015, SC-005)."""
import json

from churn import config

CAMPOS = {"fecha", "id_codificado", "probabilidad_churn", "nivel_riesgo", "version_modelo"}


def _lineas():
    return [json.loads(x) for x in config.PREDICTIONS_LOG.read_text().splitlines()]


def test_predict_registra_con_id_codificado(client, cliente_valido):
    id_ = "CLI-ABC-12345"
    assert client.post("/predict", json={**cliente_valido, "id_cliente": id_}).status_code == 200
    assert id_ not in config.PREDICTIONS_LOG.read_text()
    (linea,) = _lineas()
    assert CAMPOS <= linea.keys() and len(linea["id_codificado"]) == 16


def test_lote_registra_una_linea_por_cliente_sin_ids_en_claro(client, clientes_lote):
    clientes = [{**c, "id_cliente": f"C{i:07d}"} for i, c in enumerate(clientes_lote(30))]
    assert client.post("/predict/lote", json={"clientes": clientes}).status_code == 200
    texto = config.PREDICTIONS_LOG.read_text()
    assert len(_lineas()) == 30
    assert not any(c["id_cliente"] in texto for c in clientes)
    assert len({x["id_codificado"] for x in _lineas()}) == 30


def test_contactos_tambien_registra_sin_ids_en_claro(client, clientes_lote):
    clientes = [{**c, "id_cliente": f"K{i:07d}"} for i, c in enumerate(clientes_lote(25))]
    assert client.post("/campana/contactos", json={"clientes": clientes}).status_code == 200
    assert len(_lineas()) == 25
    assert not any(c["id_cliente"] in config.PREDICTIONS_LOG.read_text() for c in clientes)


def test_sin_id_se_registra_null_y_no_se_registran_datos_del_cliente(client, cliente_valido):
    client.post("/predict", json=cliente_valido)
    (linea,) = _lineas()
    assert linea["id_codificado"] is None
    texto = config.PREDICTIONS_LOG.read_text()
    assert "cargo_mensual" not in texto and "efectivo" not in texto


def test_entrada_invalida_no_registra(client, cliente_valido):
    client.post("/predict", json={**cliente_valido, "antiguedad_meses": 999, "id_cliente": "SECRETO1"})
    assert not config.PREDICTIONS_LOG.exists()
