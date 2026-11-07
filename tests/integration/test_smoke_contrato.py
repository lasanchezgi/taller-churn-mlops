"""scripts/smoke_test.py usa el contrato de /health del spec: estado == "sano" (T111; D8)."""
import importlib.util

from churn import config


def _smoke():
    spec = importlib.util.spec_from_file_location("smoke_test", config.ROOT / "scripts" / "smoke_test.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    def __init__(self, cuerpo):
        self._c = cuerpo

    def json(self):
        return self._c


class _ClienteFalso:
    def __init__(self, health):
        self._h = health

    def get(self, ruta):
        return _Resp(self._h)

    def post(self, ruta, json=None):
        return _Resp({"probabilidad_churn": 0.5, "nivel_riesgo": "medio"})


def test_pasa_con_la_api_real(client):
    resultados = _smoke().verificar_api(client)
    assert resultados and all(ok for _, ok, _ in resultados)


def test_pasa_con_el_contrato_del_spec():
    c = _ClienteFalso({"estado": "sano", "version_modelo": "1.0.0"})
    assert all(ok for _, ok, _ in _smoke().verificar_api(c))


def test_falla_con_el_contrato_viejo_status_ok():
    c = _ClienteFalso({"status": "ok", "version_modelo": "1.0.0"})
    ok_health = {n: ok for n, ok, _ in _smoke().verificar_api(c)}["API /health"]
    assert ok_health is False


def test_las_rutas_de_lote_campana_drift_y_panel_pasan(client, clientes_lote):
    resultados = _smoke().verificar_rutas(client, clientes_lote(120))
    assert [n for n, _, _ in resultados] == ["API /predict/lote", "API /campana/contactos", "API /drift", "API /dashboard"]
    assert all(ok for _, ok, _ in resultados)
