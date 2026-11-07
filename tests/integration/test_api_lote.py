"""POST /predict/lote y su resumen (T027, T033, T074; FR-009, FR-010, SC-003, SC-008)."""
import json
import time

import pytest

from churn import config


def test_mil_clientes_en_orden_y_en_menos_de_10_segundos(client, clientes_lote):
    clientes = clientes_lote(1000)
    t0 = time.perf_counter()
    r = client.post("/predict/lote", json={"clientes": clientes})
    assert time.perf_counter() - t0 < 10
    assert r.status_code == 200
    preds = r.json()["predicciones"]
    assert len(preds) == 1000
    for i in (0, 499, 999):
        unica = client.post("/predict", json=clientes[i]).json()
        assert preds[i]["probabilidad_churn"] == pytest.approx(unica["probabilidad_churn"])
        assert preds[i]["version_modelo"] == unica["version_modelo"]


def test_incluye_aviso_y_no_devuelve_identificadores(client, clientes_lote):
    clientes = clientes_lote(25, con_id=True)
    r = client.post("/predict/lote", json={"clientes": clientes})
    assert r.status_code == 200 and r.json()["aviso_uso_responsable"] == config.AVISO_USO_RESPONSABLE
    assert not any(c["id_cliente"] in r.text for c in clientes)


def test_mas_de_mil_se_rechaza_con_el_limite(client, cliente_valido):
    r = client.post("/predict/lote", json={"clientes": [cliente_valido] * 1001})
    assert r.status_code == 422
    d = r.json()["detalle"][0]
    assert d["campo"] == "clientes" and "1000" in d["mensaje"]


def test_lote_vacio_se_rechaza(client):
    r = client.post("/predict/lote", json={"clientes": []})
    assert r.status_code == 422 and r.json()["detalle"][0]["campo"] == "clientes"


def test_cliente_invalido_rechaza_todo_e_indica_posicion_y_campo(client, clientes_lote):
    clientes = clientes_lote(10)
    clientes[2]["antiguedad_meses"] = 121
    r = client.post("/predict/lote", json={"clientes": clientes})
    assert r.status_code == 422 and "predicciones" not in r.json()
    d = r.json()["detalle"][0]
    assert d["posicion_cliente"] == 3 and d["campo"] == "antiguedad_meses"
    assert "120" in d["mensaje"]


def test_resumen_coincide_con_el_calculo_manual_y_se_guarda(client, clientes_lote):
    clientes = clientes_lote(300, con_id=True)
    cuerpo = client.post("/predict/lote", json={"clientes": clientes}).json()
    altos = [i for i, p in enumerate(cuerpo["predicciones"]) if p["nivel_riesgo"] == "alto"]
    ingresos = sum(clientes[i]["cargo_mensual"] for i in altos)
    res = cuerpo["resumen"]
    assert res["total_clientes"] == 300 and res["clientes_riesgo_alto"] == len(altos)
    assert res["porcentaje_riesgo_alto"] == pytest.approx(100 * len(altos) / 300)
    assert res["ingresos_mensuales_en_riesgo"] == pytest.approx(ingresos)
    assert res["ingresos_6_meses_en_riesgo"] == pytest.approx(ingresos * 6)
    guardado = json.loads(config.ULTIMO_LOTE_PATH.read_text())
    assert guardado == res and "C42" not in config.ULTIMO_LOTE_PATH.read_text()


def test_lote_sin_riesgo_alto_da_ceros(client, cliente_fiel):
    res = client.post("/predict/lote", json={"clientes": [cliente_fiel] * 25}).json()["resumen"]
    assert res["clientes_riesgo_alto"] == 0 and res["ingresos_mensuales_en_riesgo"] == 0
    assert res["ingresos_6_meses_en_riesgo"] == 0


def test_lote_de_menos_de_20_no_publica_resumen(client, clientes_lote):
    cuerpo = client.post("/predict/lote", json={"clientes": clientes_lote(19)}).json()
    assert cuerpo["resumen"] is None and "demasiado pequeño" in cuerpo["mensaje_resumen"]
    assert len(cuerpo["predicciones"]) == 19 and not config.ULTIMO_LOTE_PATH.exists()


def test_sin_modelo_responde_503(client_sin_modelo, cliente_valido):
    r = client_sin_modelo.post("/predict/lote", json={"clientes": [cliente_valido]})
    assert r.status_code == 503 and r.json() == {"error": "Modelo no disponible"}
