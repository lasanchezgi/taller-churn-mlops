"""Catálogo fijo de recomendaciones, una por nivel de riesgo (T021, T086; FR-003, FR-017)."""

# TODO(retencion): textos provisionales; los define Retención y los revisa Legal
CATALOGO = {
    "alto": "Contactar con oferta de retención; revisión humana antes de actuar",
    "medio": "Incluir en seguimiento; contactar solo si queda presupuesto",
    "bajo": "No actuar",
}

# Ampliable por Legal. Ningún texto puede sugerir negar servicio ni cambiar precios (FR-003)
TERMINOS_PROHIBIDOS = (
    "negar", "suspender", "cancelar el servicio", "subir el precio", "aumentar la tarifa", "cobrar más",
)


def validar_catalogo(catalogo: dict, prohibidos=TERMINOS_PROHIBIDOS) -> None:
    """Lanza ValueError si algún texto contiene un término prohibido."""
    for nivel, texto in catalogo.items():
        for termino in prohibidos:
            if termino in texto.lower():
                raise ValueError(f"recomendación '{nivel}' contiene el término prohibido '{termino}'")


validar_catalogo(CATALOGO)  # falla al importar si el catálogo es inválido
