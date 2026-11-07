"""Seguimiento opcional: ejemplo de entrada y falta del extra (T139; FR-029; constitución IV; D11)."""
import sys

import pytest

from churn import config, seguimiento
from churn.dataset import generar


def test_el_ejemplo_de_entrada_no_trae_id_ni_edad():
    ejemplo = seguimiento.ejemplo_entrada(generar(200))
    assert list(ejemplo.columns) == config.FEATURES
    assert config.ID_COL not in ejemplo.columns and config.SENSITIVE_COL not in ejemplo.columns
    assert 1 <= len(ejemplo) <= 5


def test_sin_el_extra_el_mensaje_dice_como_instalarlo(monkeypatch):
    monkeypatch.setitem(sys.modules, "mlflow", None)  # simula que no está instalado
    with pytest.raises(SystemExit) as e:
        seguimiento.importar_mlflow()
    assert "uv sync --extra mlflow" in str(e.value)
