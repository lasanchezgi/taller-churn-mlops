"""Límite de solicitudes por IP en la API (T069, T078; FR-020)."""
from churn import config


def test_supera_el_limite_responde_429_con_formato_de_error(client, monkeypatch):
    limite = 5
    client.app.state.limitador.limite = limite
    codigos = [client.get("/health").status_code for _ in range(limite + 3)]
    assert codigos[:limite] == [200] * limite
    assert codigos[limite:] == [429] * 3
    r = client.get("/health")
    assert set(r.json()) == {"error"} and "Demasiadas solicitudes" in r.json()["error"]
    assert int(r.headers["Retry-After"]) >= 1


def test_el_limite_por_defecto_viene_de_config(client):
    assert client.app.state.limitador.limite == config.LIMITE_SOLICITUDES_POR_MINUTO == 60
