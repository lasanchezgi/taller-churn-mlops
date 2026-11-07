"""El catálogo no sugiere negar servicio ni cambiar precios (T076, T086; FR-003, FR-017)."""
import pytest

from churn.recomendaciones import CATALOGO, TERMINOS_PROHIBIDOS, validar_catalogo

REQUERIDOS = ("negar", "suspender", "cancelar el servicio", "subir el precio", "aumentar la tarifa", "cobrar más")


def test_el_catalogo_trae_un_texto_por_nivel():
    assert set(CATALOGO) == {"alto", "medio", "bajo"} and all(CATALOGO.values())


@pytest.mark.parametrize("termino", REQUERIDOS)
def test_ningun_texto_contiene_el_termino(termino):
    assert termino in TERMINOS_PROHIBIDOS
    assert all(termino not in t.lower() for t in CATALOGO.values())


def test_la_validacion_rechaza_un_catalogo_con_termino_prohibido():
    with pytest.raises(ValueError, match="prohibido"):
        validar_catalogo({**CATALOGO, "alto": "Se va a Subir el precio al cliente"})


def test_legal_puede_ampliar_la_lista():
    with pytest.raises(ValueError):
        validar_catalogo(CATALOGO, prohibidos=("retención",))
