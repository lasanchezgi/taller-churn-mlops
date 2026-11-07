"""Alerta de equidad en las respuestas y `alertas` en /health (T124; FR-026, FR-028; D2, D8)."""
RAZON = "brecha de recall entre grupos de edad 0.147 > 0.05"


def _card(client):
    return client.app.state.modelo["card"]


def _no_aprobado(client, monkeypatch):
    monkeypatch.setitem(_card(client), "aprobado_para_despliegue", False)
    monkeypatch.setitem(_card(client), "razones_no_aprobado", [RAZON])


def _aprobado(client, monkeypatch):
    monkeypatch.setitem(_card(client), "aprobado_para_despliegue", True)
    monkeypatch.setitem(_card(client), "razones_no_aprobado", [])


def test_predict_trae_la_alerta_con_la_razon_ademas_del_aviso(client, cliente_valido, monkeypatch):
    _no_aprobado(client, monkeypatch)
    d = client.post("/predict", json=cliente_valido).json()
    assert RAZON in d["alerta_equidad"] and d["aviso_uso_responsable"]


def test_cada_prediccion_del_lote_trae_la_alerta(client, clientes_lote, monkeypatch):
    _no_aprobado(client, monkeypatch)
    preds = client.post("/predict/lote", json={"clientes": clientes_lote(25)}).json()["predicciones"]
    assert len(preds) == 25 and all(RAZON in p["alerta_equidad"] for p in preds)


def test_la_lista_de_contacto_conserva_aviso_pero_no_requiere_alerta(client, cliente_riesgoso, monkeypatch):
    _no_aprobado(client, monkeypatch)
    r = client.post("/campana/contactos", json={"clientes": [cliente_riesgoso]}).json()
    assert r["aviso_uso_responsable"]


def test_sin_alerta_si_el_modelo_esta_aprobado(client, cliente_valido, clientes_lote, monkeypatch):
    _aprobado(client, monkeypatch)
    assert "alerta_equidad" not in client.post("/predict", json=cliente_valido).json()
    preds = client.post("/predict/lote", json={"clientes": clientes_lote(20)}).json()["predicciones"]
    assert all("alerta_equidad" not in p for p in preds)


def test_health_no_aprobado_sigue_sano_pero_avisa(client, monkeypatch):
    _no_aprobado(client, monkeypatch)
    r = client.get("/health")
    d = r.json()
    assert r.status_code == 200 and d["estado"] == "sano" and d["modelo_cargado"] is True
    assert d["aprobado_para_despliegue"] is False and d["alertas"] == [RAZON]


def test_health_aprobado_no_tiene_alertas(client, monkeypatch):
    _aprobado(client, monkeypatch)
    d = client.get("/health").json()
    assert d["aprobado_para_despliegue"] is True and d["alertas"] == []


def test_health_sin_modelo_tiene_lista_de_alertas_vacia(client_sin_modelo):
    d = client_sin_modelo.get("/health").json()
    assert d["estado"] == "no_sano" and d["alertas"] == []
