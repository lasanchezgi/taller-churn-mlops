"""Catálogo de recomendaciones (T018; FR-003, FR-017)."""
from churn.recomendaciones import CATALOGO


def test_una_entrada_por_nivel():
    assert set(CATALOGO) == {"alto", "medio", "bajo"}
    assert all(isinstance(t, str) and t.strip() for t in CATALOGO.values())


def test_el_nivel_alto_exige_revision_humana():
    assert "revisión humana" in CATALOGO["alto"]


def test_ningun_texto_niega_servicio_ni_cambia_precios():
    for texto in CATALOGO.values():
        for malo in ("negar", "suspender", "subir", "tarifa", "cobrar"):
            assert malo not in texto.lower()
