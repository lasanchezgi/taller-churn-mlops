"""Formato de id_cliente (T075; FR-006, FR-007)."""
import pytest
from pydantic import ValidationError

from churn.api import Cliente


@pytest.fixture
def base(cliente_valido):
    return cliente_valido


@pytest.mark.parametrize("id_", ["A", "abc-DEF_123", "x" * 64, "0123456789"])
def test_acepta_letras_numeros_guion_y_guion_bajo(base, id_):
    assert Cliente(**base, id_cliente=id_).id_cliente == id_


@pytest.mark.parametrize("id_", ["x" * 65, "a b", "a.b", "a/b", "a@b", "ñandú", "", "a;b", "<s>"])
def test_rechaza_largo_excedido_y_otros_simbolos(base, id_):
    with pytest.raises(ValidationError):
        Cliente(**base, id_cliente=id_)


def test_es_opcional(base):
    assert Cliente(**base).id_cliente is None
