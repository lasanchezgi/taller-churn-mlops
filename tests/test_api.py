"""Pruebas de la API con TestClient (T014/T020/T025; FR-001, FR-006..008, SC-001, SC-002)."""
from churn import config


def _errores(r):
    """Respuesta 422 → {campo: mensaje}."""
    assert r.status_code == 422
    assert r.json()["error"] == "Entrada inválida"
    return {d["campo"]: d["mensaje"] for d in r.json()["detalle"]}


def test_caso_feliz_devuelve_la_prediccion_completa(client, cliente_valido):
    r = client.post("/predict", json=cliente_valido)
    assert r.status_code == 200
    d = r.json()
    assert set(d) - {"alerta_equidad"} == {"probabilidad_churn", "nivel_riesgo", "recomendacion",
                      "version_modelo", "aviso_uso_responsable"}
    assert 0 <= d["probabilidad_churn"] <= 1
    assert d["nivel_riesgo"] in {"alto", "medio", "bajo"}
    assert d["recomendacion"]
    assert d["version_modelo"] == config.MODEL_VERSION
    assert d["aviso_uso_responsable"]


def test_rechaza_cargo_negativo_y_nombra_el_campo(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "cargo_mensual": -10})
    assert "cargo_mensual" in _errores(r)


def test_rechaza_tipo_plan_invalido_y_lista_los_permitidos(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "tipo_plan": "vip"})
    mensaje = _errores(r)["tipo_plan"]
    assert all(plan in mensaje for plan in config.PLANES)
    assert "vip" not in mensaje  # no repite el valor recibido


def test_rechaza_campo_extra_cedula_sin_repetir_su_valor(client, cliente_valido):
    r = client.post("/predict", json={**cliente_valido, "cedula": "1234567890"})
    assert _errores(r)["cedula"] == "campo no previsto"
    assert "1234567890" not in r.text


def test_rechaza_campo_faltante(client, cliente_valido):
    del cliente_valido["reclamos_ult_3m"]
    assert _errores(client.post("/predict", json=cliente_valido))["reclamos_ult_3m"] == "campo obligatorio"


def test_cliente_riesgoso_tiene_mayor_probabilidad_que_uno_fiel(client, cliente_riesgoso, cliente_fiel):
    p_riesgoso = client.post("/predict", json=cliente_riesgoso).json()["probabilidad_churn"]
    p_fiel = client.post("/predict", json=cliente_fiel).json()["probabilidad_churn"]
    assert p_riesgoso > p_fiel


def test_health_sano_con_modelo(client, cliente_valido):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["estado"] == "sano" and d["modelo_cargado"] is True and d["error"] is None
    assert d["version_modelo"] == client.post("/predict", json=cliente_valido).json()["version_modelo"]
    assert isinstance(d["aprobado_para_despliegue"], bool)


def test_health_no_sano_sin_modelo(client_sin_modelo):
    r = client_sin_modelo.get("/health")
    assert r.status_code == 503
    assert r.json() == {"estado": "no_sano", "modelo_cargado": False, "version_modelo": None,
                        "aprobado_para_despliegue": None, "alertas": [], "error": "Modelo no disponible"}
    assert ".joblib" not in r.text
