"""scripts/promover_modelo.py (T140; FR-030, SC-012; D11)."""
import importlib.util

import pytest

from churn import config, seguimiento
from churn.dataset import generar
from churn.train import entrenar, guardar_modelo

mlflow = pytest.importorskip("mlflow")
NOMBRE = config.MLFLOW_MODELO_REGISTRADO


def _script():
    spec = importlib.util.spec_from_file_location("promover_modelo", config.ROOT / "scripts" / "promover_modelo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def entrenado(tmp_path_factory):
    res = entrenar(generar(1500), "logreg")
    ruta = tmp_path_factory.mktemp("m") / "m.joblib"
    return res, guardar_modelo(res, ruta, ruta.parent / "card.json")


@pytest.fixture
def registro(tmp_path, monkeypatch, entrenado):
    """Registra una versión candidata en un seguimiento temporal; devuelve una función según la aprobación."""
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    monkeypatch.setattr(config, "MLFLOW_ARTIFACTS_DIR", tmp_path / "mlruns")
    res, card = entrenado

    def registrar(aprobado: bool):
        seguimiento.registrar_entrenamiento(res, {**card, "aprobado_para_despliegue": aprobado})
        return mlflow.MlflowClient(config.MLFLOW_TRACKING_URI)
    return registrar


def _alias_produccion(client):
    try:
        return client.get_model_version_by_alias(NOMBRE, "produccion")
    except Exception:
        return None


def test_no_aprobado_sin_forzar_falla_y_no_asigna(registro):
    client = registro(False)
    with pytest.raises(SystemExit) as e:
        _script().main([])
    assert "no está aprobada" in str(e.value)
    assert _alias_produccion(client) is None


def test_aprobado_asigna_produccion(registro):
    client = registro(True)
    _script().main([])
    v = _alias_produccion(client)
    assert v is not None and v.tags["promocion_forzada"] == "false"


def test_forzar_sin_motivo_falla_y_no_asigna(registro):
    client = registro(False)
    with pytest.raises(SystemExit) as e:
        _script().main(["--forzar"])
    assert "--motivo" in str(e.value)
    assert _alias_produccion(client) is None


def test_forzar_con_motivo_asigna_y_lo_registra(registro):
    client = registro(False)
    _script().main(["--forzar", "--motivo", "revisión del dueño del modelo, ticket 123"])
    v = _alias_produccion(client)
    assert v.tags["promocion_forzada"] == "true"
    assert v.tags["motivo_forzado"] == "revisión del dueño del modelo, ticket 123"


def test_motivo_en_blanco_no_cuenta(registro):
    client = registro(False)
    with pytest.raises(SystemExit):
        _script().main(["--forzar", "--motivo", "   "])
    assert _alias_produccion(client) is None


def test_sin_version_candidata_falla(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    monkeypatch.setattr(config, "MLFLOW_ARTIFACTS_DIR", tmp_path / "mlruns")
    with pytest.raises(SystemExit) as e:
        _script().main([])
    assert "candidato" in str(e.value)
