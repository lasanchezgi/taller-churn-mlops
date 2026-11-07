"""POST /campana/contactos (T038; FR-005, FR-011, FR-012, SC-007; D5)."""
import pytest

from churn import config


def _riesgosos(cliente_riesgoso, n):
    return [{**cliente_riesgoso, "cargo_mensual": 20.0 + (i % 80)} for i in range(n)]


def test_precondicion_el_cliente_riesgoso_es_de_riesgo_alto(client, cliente_riesgoso):
    assert client.post("/predict", json=cliente_riesgoso).json()["nivel_riesgo"] == "alto"


def test_por_defecto_son_250_contactos_y_2000_usd(client, cliente_riesgoso):
    r = client.post("/campana/contactos", json={"clientes": _riesgosos(cliente_riesgoso, 300)})
    assert r.status_code == 200
    c = r.json()
    assert len(c["contactos"]) == 250 and c["costo_total"] == 2000.0 and c["max_contactos"] == 250
    assert c["aviso_uso_responsable"] == config.AVISO_USO_RESPONSABLE
    ingresos = [x["ingreso_esperado"] for x in c["contactos"]]
    assert ingresos == sorted(ingresos, reverse=True)
    assert len({x["posicion_en_lote"] for x in c["contactos"]}) == 250


def test_con_pocos_en_riesgo_devuelve_solo_esos(client, cliente_riesgoso, cliente_fiel):
    clientes = _riesgosos(cliente_riesgoso, 10) + [cliente_fiel] * 20
    c = client.post("/campana/contactos", json={"clientes": clientes}).json()
    assert len(c["contactos"]) == 10 and c["costo_total"] == 80.0


def test_id_cliente_solo_en_esta_respuesta_y_si_se_envio(client, cliente_riesgoso):
    clientes = _riesgosos(cliente_riesgoso, 3)
    clientes[0]["id_cliente"] = "ABC-1"
    c = client.post("/campana/contactos", json={"clientes": clientes}).json()
    con_id = [x for x in c["contactos"] if "id_cliente" in x]
    assert len(con_id) == 1 and con_id[0]["id_cliente"] == "ABC-1"


def test_presupuesto_menor_que_el_costo_da_lista_vacia(client, cliente_riesgoso):
    c = client.post("/campana/contactos", json={"clientes": _riesgosos(cliente_riesgoso, 5),
                                                "presupuesto": 5}).json()
    assert c["contactos"] == [] and c["mensaje"]


@pytest.mark.parametrize("campo,valor", [("presupuesto", 0), ("presupuesto", 100_000.01),
                                         ("costo_por_contacto", 0), ("costo_por_contacto", 1000.01)])
def test_presupuesto_o_costo_fuera_de_limites_dan_422(client, cliente_valido, campo, valor):
    r = client.post("/campana/contactos", json={"clientes": [cliente_valido], campo: valor})
    assert r.status_code == 422 and r.json()["detalle"][0]["campo"] == campo


def test_acepta_la_base_completa_y_rechaza_mas(client, cliente_valido):
    ok = client.post("/campana/contactos", json={"clientes": [cliente_valido] * config.CONTACTOS_LOTE_MAX})
    assert ok.status_code == 200
    mas = client.post("/campana/contactos", json={"clientes": [cliente_valido] * (config.CONTACTOS_LOTE_MAX + 1)})
    assert mas.status_code == 422 and "5000" in mas.json()["detalle"][0]["mensaje"]


def test_sin_modelo_responde_503(client_sin_modelo, cliente_valido):
    assert client_sin_modelo.post("/campana/contactos", json={"clientes": [cliente_valido]}).status_code == 503
