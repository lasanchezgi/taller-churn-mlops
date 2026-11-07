"""Resumen de riesgo y selección de contactos (T032, T037, T074; FR-010..012, SC-007, SC-008; D5)."""
import pytest

from churn import campana, config


def _p(prob, nivel):
    return {"probabilidad_churn": prob, "nivel_riesgo": nivel, "recomendacion": "r"}


def test_max_contactos_es_el_entero_de_presupuesto_sobre_costo():
    assert campana.max_contactos(2000, 8) == 250
    assert campana.max_contactos(2010, 8) == 251
    assert campana.max_contactos(0.3, 0.1) == 3  # sin error de coma flotante


def test_resumen_calculado_a_mano():
    preds = [_p(0.9, "alto")] * 5 + [_p(0.6, "medio")] * 5 + [_p(0.1, "bajo")] * 10
    cargos = [100.0] * 5 + [999.0] * 5 + [50.0] * 10
    r = campana.resumir_lote(preds, cargos, "1.0.0")
    assert r["total_clientes"] == 20 and r["clientes_riesgo_alto"] == 5
    assert r["porcentaje_riesgo_alto"] == 25.0
    assert r["ingresos_mensuales_en_riesgo"] == 500.0 and r["ingresos_6_meses_en_riesgo"] == 3000.0
    assert r["version_modelo"] == "1.0.0" and r["fecha"]


def test_resumen_sin_riesgo_alto_da_ceros():
    r = campana.resumir_lote([_p(0.1, "bajo")] * 20, [80.0] * 20, "1.0.0")
    assert r["clientes_riesgo_alto"] == 0 and r["ingresos_mensuales_en_riesgo"] == 0


def test_resumen_exige_el_minimo_de_clientes():
    assert campana.resumir_lote([_p(0.9, "alto")] * (config.MIN_LOTE_RESUMEN - 1),
                                [10.0] * (config.MIN_LOTE_RESUMEN - 1), "1.0.0") is None


def test_ordena_por_ingreso_esperado_y_solo_riesgo_alto():
    preds = [_p(0.9, "alto"), _p(0.8, "alto"), _p(0.95, "alto"), _p(0.6, "medio")]
    cargos = [100.0, 200.0, 50.0, 1000.0]  # esperado: 90, 160, 47.5, (medio: fuera)
    r = campana.seleccionar_contactos(preds, cargos)
    assert [c["posicion_en_lote"] for c in r["contactos"]] == [2, 1, 3]
    assert r["clientes_en_riesgo_alto"] == 3 and r["costo_total"] == 24.0
    assert r["contactos"][0]["ingreso_esperado"] == pytest.approx(160.0)


def test_empate_de_ingreso_respeta_el_orden_de_entrada():
    preds = [_p(0.8, "alto")] * 3
    r = campana.seleccionar_contactos(preds, [100.0] * 3)
    assert [c["posicion_en_lote"] for c in r["contactos"]] == [1, 2, 3]


def test_toma_el_menor_entre_presupuesto_y_clientes_en_riesgo():
    preds = [_p(0.9, "alto")] * 5
    assert len(campana.seleccionar_contactos(preds, [10.0] * 5, presupuesto=16, costo=8)["contactos"]) == 2
    r = campana.seleccionar_contactos(preds, [10.0] * 5)
    assert len(r["contactos"]) == 5 and r["costo_total"] == 40.0 and r["max_contactos"] == 250


def test_con_mas_de_250_en_riesgo_toma_exactamente_250():
    preds = [_p(0.9, "alto")] * 400
    r = campana.seleccionar_contactos(preds, [50.0] * 400)
    assert len(r["contactos"]) == 250 and r["costo_total"] == 2000.0


def test_presupuesto_menor_que_el_costo_da_lista_vacia_con_mensaje():
    r = campana.seleccionar_contactos([_p(0.9, "alto")], [10.0], presupuesto=5, costo=8)
    assert r["contactos"] == [] and r["costo_total"] == 0 and r["mensaje"]


def test_sin_riesgo_alto_da_lista_vacia_con_mensaje():
    r = campana.seleccionar_contactos([_p(0.2, "bajo")], [10.0])
    assert r["contactos"] == [] and "riesgo alto" in r["mensaje"]


def test_id_cliente_solo_si_se_envio():
    preds = [_p(0.9, "alto")] * 2
    r = campana.seleccionar_contactos(preds, [10.0, 10.0], ids=["A1", None])
    assert r["contactos"][0]["id_cliente"] == "A1" and "id_cliente" not in r["contactos"][1]


@pytest.mark.parametrize("presupuesto,costo", [(0, 8), (-1, 8), (2000, 0), (2000, -3)])
def test_valores_no_positivos_se_rechazan(presupuesto, costo):
    with pytest.raises(ValueError):
        campana.seleccionar_contactos([_p(0.9, "alto")], [10.0], presupuesto=presupuesto, costo=costo)
