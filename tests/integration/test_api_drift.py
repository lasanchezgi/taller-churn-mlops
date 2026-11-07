"""POST y GET /drift (T050/T109; FR-014, SC-009)."""
from churn import config
from churn.dataset import generar


def _lote(df):
    return {"clientes": df[config.FEATURES].to_dict(orient="records")}


def test_get_sin_informe_responde_404_claro(client):
    r = client.get("/drift")
    assert r.status_code == 404 and "error" in r.json()


def test_lote_parecido_al_entrenamiento_es_estable(client):
    r = client.post("/drift", json=_lote(generar(1000, seed=config.SEED + 5)))
    assert r.status_code == 200 and r.json()["estado_general"] == "estable"
    assert [v["nombre"] for v in r.json()["variables"]] == config.FEATURES


def test_variable_desplazada_es_critica(client):
    df = generar(1000, seed=config.SEED + 5)
    df["cargo_mensual"] = (df["cargo_mensual"] * 1.6).round(2)
    r = client.post("/drift", json=_lote(df)).json()
    assert r["estado_general"] == "critico" and r["recomendacion"] == "evaluar reentrenamiento"


def test_lote_pequeno_da_datos_insuficientes(client):
    r = client.post("/drift", json=_lote(generar(50)))
    assert r.json()["estado_general"] == "datos_insuficientes"


def test_el_informe_se_guarda_y_get_lo_devuelve(client):
    cuerpo = client.post("/drift", json=_lote(generar(1000, seed=config.SEED + 5))).json()
    assert config.DRIFT_REPORT_PATH.exists()
    assert client.get("/drift").json() == cuerpo


def test_lote_mayor_al_maximo_se_rechaza(client, cliente_valido):
    r = client.post("/drift", json={"clientes": [cliente_valido] * (config.LOTE_MAX + 1)})
    assert r.status_code == 422


def test_sin_modelo_responde_503(client_sin_modelo, cliente_valido):
    assert client_sin_modelo.post("/drift", json={"clientes": [cliente_valido]}).status_code == 503
