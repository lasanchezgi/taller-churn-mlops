"""El resumen de riesgo exige un mínimo de clientes (T074; FR-010)."""
from churn import campana, config


def _preds(n):
    return [{"nivel_riesgo": "alto"} for _ in range(n)]


def test_con_menos_del_minimo_no_hay_resumen():
    assert campana.resumir_lote(_preds(config.MIN_LOTE_RESUMEN - 1), [50.0] * 19, "1.0.0") is None


def test_con_el_minimo_exacto_si_hay_resumen():
    r = campana.resumir_lote(_preds(config.MIN_LOTE_RESUMEN), [50.0] * 20, "1.0.0")
    assert r["total_clientes"] == 20 and r["ingresos_mensuales_en_riesgo"] == 1000.0


def test_la_api_informa_lote_demasiado_pequeno_y_no_guarda_resumen(client, clientes_lote):
    r = client.post("/predict/lote", json={"clientes": clientes_lote(19)})
    d = r.json()
    assert r.status_code == 200 and d.get("resumen") is None
    assert "demasiado pequeño" in d["mensaje_resumen"] and "20" in d["mensaje_resumen"]
    assert not config.ULTIMO_LOTE_PATH.exists()
