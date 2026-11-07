"""Entrada `Cliente`: límites, tipos y campos no previstos (T008; FR-006, FR-007, FR-008, SC-002, SC-006)."""
import pytest
from pydantic import ValidationError

from churn.api import Cliente


@pytest.mark.parametrize("campo,valor", [
    ("antiguedad_meses", 1), ("antiguedad_meses", 120), ("reclamos_ult_3m", 0), ("reclamos_ult_3m", 6),
    ("cargo_mensual", 10), ("cargo_mensual", 1000), ("uso_datos_gb", 0), ("uso_datos_gb", 1000),
])
def test_acepta_los_limites(cliente_valido, campo, valor):
    assert getattr(Cliente(**{**cliente_valido, campo: valor}), campo) == valor  # conserva el valor, no solo "no falla"


@pytest.mark.parametrize("campo,valor", [
    ("antiguedad_meses", 0), ("antiguedad_meses", 121), ("reclamos_ult_3m", -1), ("reclamos_ult_3m", 7),
    ("cargo_mensual", 9.99), ("cargo_mensual", 1000.01), ("uso_datos_gb", -0.1), ("uso_datos_gb", 1000.1),
    ("antiguedad_meses", 12.5), ("reclamos_ult_3m", 1.5), ("antiguedad_meses", None), ("cargo_mensual", float("nan")),
    ("tipo_plan", "otro"), ("metodo_pago", "cheque"), ("renovo_contrato", "tal vez"),
])
def test_rechaza_fuera_de_rango_decimales_nulos_y_categorias(cliente_valido, campo, valor):
    with pytest.raises(ValidationError):
        Cliente(**{**cliente_valido, campo: valor})


def test_rechaza_campo_faltante(cliente_valido):
    del cliente_valido["tipo_plan"]
    with pytest.raises(ValidationError):
        Cliente(**cliente_valido)


@pytest.mark.parametrize("extra", ["rango_edad", "cedula", "nombre"])
def test_rechaza_cualquier_campo_extra_incluida_la_edad(cliente_valido, extra):
    with pytest.raises(ValidationError):
        Cliente(**cliente_valido, **{extra: "18-25"})
