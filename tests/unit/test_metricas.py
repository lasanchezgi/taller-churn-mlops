"""Pruebas de churn.metricas y GET /metrics (T058; FR-019, FR-023)."""
import pytest

from churn import config
from churn.metricas import Metricas


def test_sin_datos_no_inventa_cifras():
    r = Metricas().resumen(None)
    assert r["predicciones_totales"] == 0 and r["latencia_ms"] == {"p50": None, "p95": None}
    assert r["modelo"] is None and r["negocio"]["roi_esperado"] is None


def test_distribucion_latencia_y_errores():
    m = Metricas()
    for lat in range(1, 101):
        m.registrar_prediccion(0.8, "alto", 100.0, float(lat))
    m.registrar_prediccion(0.1, "bajo", 50.0, 1.0)
    m.registrar_error()
    r = m.resumen(None)
    assert r["distribucion_riesgo"] == {"alto": 100, "medio": 0, "bajo": 1}
    assert r["errores_totales"] == 1 and r["predicciones_totales"] == 101
    assert r["latencia_ms"]["p50"] == pytest.approx(50.0, abs=1) and r["latencia_ms"]["p95"] > 90


def test_negocio_calculado_a_mano():
    m = Metricas()
    m.registrar_prediccion(0.9, "alto", 100.0, 1.0)
    m.registrar_prediccion(0.8, "alto", 50.0, 1.0)
    m.registrar_prediccion(0.3, "bajo", 999.0, 1.0)  # no cuenta: no es riesgo alto
    n = m.resumen(None)["negocio"]
    assert n["clientes_en_riesgo"] == 2 and n["clientes_priorizados"] == 2
    assert n["ingresos_mensuales_en_riesgo"] == 150.0 and n["ingresos_6_meses_en_riesgo"] == 900.0
    assert n["costo_campana"] == 2 * config.COSTO_CONTACTO
    retenido = config.TASA_EXITO_CAMPANA * (0.9 * 100 * 6 + 0.8 * 50 * 6)
    assert n["roi_esperado"] == pytest.approx((retenido - 16) / 16, abs=1e-3)


def test_priorizados_no_superan_el_presupuesto():
    m = Metricas()
    for _ in range(300):
        m.registrar_prediccion(0.9, "alto", 10.0, 1.0)
    n = m.resumen(None)["negocio"]
    assert n["clientes_en_riesgo"] == 300 and n["clientes_priorizados"] == 250
    assert n["costo_campana"] == 2000.0


def test_metrics_en_la_api(client, cliente_valido, cliente_riesgoso):
    assert client.post("/predict", json=cliente_riesgoso).status_code == 200
    assert client.post("/predict", json={**cliente_valido, "cargo_mensual": -1}).status_code == 422
    r = client.get("/metrics")
    assert r.status_code == 200
    d = r.json()
    assert d["predicciones_totales"] == 1 and d["errores_totales"] == 1
    assert d["modelo"]["version"] == config.MODEL_VERSION and "umbral" in d["modelo"]
    assert "recall" in d["modelo"]["metricas_offline"] and d["latencia_ms"]["p50"] > 0
    assert "id_cliente" not in r.text


def test_metrics_sin_modelo_cuenta_el_503(client_sin_modelo, cliente_valido):
    assert client_sin_modelo.post("/predict", json=cliente_valido).status_code == 503
    d = client_sin_modelo.get("/metrics").json()
    assert d["errores_totales"] == 1 and d["modelo"] is None
