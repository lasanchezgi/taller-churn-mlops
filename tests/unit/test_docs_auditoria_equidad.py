"""La auditoría trimestral de equidad está documentada con sus partes (T087; FR-025, FR-005)."""
from churn import config

TEXTO = (config.ROOT / "docs" / "AUDITORIA_EQUIDAD.md").read_text(encoding="utf-8")


def test_define_el_cruce_con_la_edad_del_sistema_de_origen():
    assert "sistema de origen" in TEXTO and "id_codificado" in TEXTO and "CHURN_HASH_SALT" in TEXTO


def test_usa_los_criterios_de_config():
    assert str(config.MAX_DIF_RECALL).replace(".", ",") in TEXTO
    assert str(config.MIN_RATIO_IMPACTO).replace(".", ",") in TEXTO
    assert str(config.MIN_GRUPO_AUDITORIA) in TEXTO


def test_trae_plantilla_de_informe_y_revision_humana_con_nombre_y_fecha():
    assert "Informe del trimestre" in TEXTO
    assert "analista de retención" in TEXTO and "nombre del analista y la fecha" in TEXTO
