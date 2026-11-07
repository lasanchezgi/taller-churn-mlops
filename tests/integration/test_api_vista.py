"""GET /metrics con último lote y último informe, y GET /dashboard (T056; FR-010, FR-014, FR-019)."""
from churn import config
from churn.dataset import generar


def test_metrics_sin_lote_ni_informe_devuelve_nulos(client):
    m = client.get("/metrics").json()
    assert m["ultimo_resumen"] is None and m["ultimo_cambio_datos"] is None


def test_metrics_con_lote_e_informe_sin_identificadores(client, clientes_lote):
    clientes = clientes_lote(1000, con_id=True)
    resumen = client.post("/predict/lote", json={"clientes": clientes}).json()["resumen"]
    sin_id = [{k: v for k, v in c.items() if k != "id_cliente"} for c in clientes]
    client.post("/drift", json={"clientes": sin_id})
    r = client.get("/metrics")
    m = r.json()
    assert m["ultimo_resumen"] == resumen
    assert m["ultimo_cambio_datos"]["estado_general"] in ("estable", "alerta", "critico")
    assert "simulacion" not in m["ultimo_cambio_datos"]
    assert not any(c["id_cliente"] in r.text for c in clientes)


def test_dashboard_responde_html(client):
    r = client.get("/dashboard")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "Monitor de Churn" in r.text


def test_dashboard_funciona_sin_modelo(client_sin_modelo):
    assert client_sin_modelo.get("/dashboard").status_code == 200
