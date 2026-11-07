"""La API no crea, modifica ni borra datos del cliente (T099; FR-017)."""
from fastapi.routing import APIRoute

POST_PERMITIDOS = {"/predict", "/predict/lote", "/campana/contactos", "/drift"}


def test_solo_hay_rutas_get_y_post(client):
    metodos = {m for r in client.app.routes if isinstance(r, APIRoute) for m in r.methods}
    assert metodos == {"GET", "POST"}


def test_los_post_son_solo_de_puntuacion_o_comparacion(client):
    posts = {r.path for r in client.app.routes if isinstance(r, APIRoute) and "POST" in r.methods}
    assert posts == POST_PERMITIDOS


def test_put_patch_y_delete_no_existen(client, cliente_valido):
    for ruta in ("/predict", "/predict/lote", "/campana/contactos", "/health"):
        for metodo in ("put", "patch", "delete"):
            assert getattr(client, metodo)(ruta).status_code == 405
