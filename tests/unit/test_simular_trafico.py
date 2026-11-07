"""scripts/simular_trafico.py (T113; FR-014; D6)."""
import importlib.util
import json
import urllib.error

import pytest

from churn import config
from churn.dataset import aplicar_crisis
from churn.features import cargar_datos


def _modulo():
    spec = importlib.util.spec_from_file_location("simular_trafico", config.ROOT / "scripts" / "simular_trafico.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_un_404_se_informa_como_error_http(monkeypatch):
    mod = _modulo()

    def falla(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(mod.urllib.request, "urlopen", falla)
    with pytest.raises(SystemExit) as e:
        mod.main(["--n", "10"])
    assert "404" in str(e.value) and "No se pudo conectar" not in str(e.value)


def test_sin_servidor_se_informa_que_no_se_pudo_conectar(monkeypatch):
    mod = _modulo()

    def falla(req, timeout=0):
        raise urllib.error.URLError("rechazada")

    monkeypatch.setattr(mod.urllib.request, "urlopen", falla)
    with pytest.raises(SystemExit) as e:
        mod.main(["--n", "10"])
    assert "No se pudo conectar" in str(e.value)


def test_la_crisis_sale_de_aplicar_crisis_sobre_el_csv(monkeypatch):
    mod = _modulo()
    cuerpos = []

    class _Ok:
        def read(self):
            return b"{}"

    def captura(req, timeout=0):
        cuerpos.append(json.loads(req.data))
        return _Ok()

    monkeypatch.setattr(mod.urllib.request, "urlopen", captura)
    mod.main(["--escenario", "crisis", "--n", "100"])
    esperado = aplicar_crisis(cargar_datos(config.DATA_RAW)).sample(n=100, random_state=config.SEED)
    enviados = [c["cargo_mensual"] for c in cuerpos[0]["clientes"]]
    assert enviados == esperado["cargo_mensual"].tolist()
