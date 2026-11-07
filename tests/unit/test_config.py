"""Constantes de config (T002/T103; FR-006, FR-008, FR-009, FR-011, FR-018, FR-020, SC-010)."""
from churn import config


def test_features_sin_atributos_sensibles_ni_id():
    for prohibido in ("rango_edad", "id_cliente", "periodo", "churn"):
        assert prohibido not in config.FEATURES


def test_constantes_de_las_decisiones():
    assert config.LOTE_MAX == 1000 and config.CONTACTOS_LOTE_MAX == 5000
    assert config.MIN_PRECISION_TOP == 0.40 and config.MIN_ROI == 3
    assert config.MIN_RATIO_IMPACTO == 0.80 and config.TOP_EVALUACION == 0.05
    assert config.MAX_DIF_RECALL == 0.05 and config.MIN_FILAS_DRIFT == 100
    assert config.LIMITE_SOLICITUDES_POR_MINUTO == 60 and config.MIN_LOTE_RESUMEN == 20


def test_limites_de_presupuesto_y_costo():
    assert (config.PRESUPUESTO_MIN, config.PRESUPUESTO_MAX) == (0.01, 100_000)
    assert (config.COSTO_CONTACTO_MIN, config.COSTO_CONTACTO_MAX) == (0.01, 1000)


def test_rutas_de_reportes_y_vista():
    assert config.ULTIMO_LOTE_PATH.name == "ultimo_lote.json"
    assert config.DASHBOARD_PATH.name == "index.html"
