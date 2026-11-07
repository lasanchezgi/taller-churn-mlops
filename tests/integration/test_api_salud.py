"""GET /health (T043; FR-013, FR-028)."""


def test_con_modelo_esta_sano_y_trae_la_version(client):
    r = client.get("/health")
    d = r.json()
    assert r.status_code == 200 and d["estado"] == "sano" and d["modelo_cargado"] is True
    assert d["version_modelo"] and d["error"] is None


def test_sin_modelo_responde_503_no_sano_y_no_predice(client_sin_modelo, cliente_valido, clientes_lote):
    r = client_sin_modelo.get("/health")
    assert r.status_code == 503 and r.json()["estado"] == "no_sano" and r.json()["modelo_cargado"] is False
    for ruta, cuerpo in (("/predict", cliente_valido), ("/predict/lote", {"clientes": clientes_lote(3)}),
                         ("/campana/contactos", {"clientes": clientes_lote(3)})):
        r = client_sin_modelo.post(ruta, json=cuerpo)
        assert r.status_code == 503 and "probabilidad_churn" not in r.text
