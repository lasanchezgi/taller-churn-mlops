"""Pruebas de churn.train (T014/T015; FR-016, FR-018, SC-004)."""
import hashlib
import json

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import recall_score

from churn import config, train
from churn.dataset import generar
from churn.features import particionar


@pytest.fixture(scope="module")
def datos():
    return generar(2000)


def test_modelo_es_pipeline_con_regresion_balanceada():
    pipe = train.construir_modelo("logreg")
    clf = pipe.named_steps["clf"]
    assert isinstance(clf, LogisticRegression)
    assert clf.class_weight == "balanced"
    assert clf.random_state == config.SEED


def test_algoritmo_rf_usa_random_forest():
    assert isinstance(train.construir_modelo("rf").named_steps["clf"], RandomForestClassifier)


def test_algoritmo_desconocido_se_rechaza():
    with pytest.raises(ValueError, match="algoritmo"):
        train.construir_modelo("xgb")


def test_umbral_cumple_recall_minimo_en_train(datos):
    tr, _ = particionar(datos)
    X, y = tr[config.FEATURES], tr[config.TARGET]
    umbral, regla = train.calibrar_umbral(train.construir_modelo("logreg"), X, y)
    assert regla == "mayor_precision_con_recall"
    cv = StratifiedKFold(5, shuffle=True, random_state=config.SEED)
    proba = cross_val_predict(train.construir_modelo("logreg"), X, y, cv=cv,
                              method="predict_proba")[:, 1]
    assert 0 < umbral < 1
    assert recall_score(y, proba >= umbral) >= config.MIN_RECALL


def test_dos_corridas_dan_metricas_identicas(datos):
    a = train.entrenar(datos, "logreg")["metricas"]
    b = train.entrenar(datos, "logreg")["metricas"]
    assert a == b


def test_el_umbral_se_calibra_solo_con_train(datos, monkeypatch):
    tr, te = particionar(datos)
    vistos = []
    original = train.calibrar_umbral

    def espia(pipe, X, y):
        vistos.append(X.index)
        return original(pipe, X, y)

    monkeypatch.setattr(train, "calibrar_umbral", espia)
    train.entrenar(datos, "logreg")
    assert list(vistos[0]) == list(tr.index)
    assert set(vistos[0]).isdisjoint(te.index)


def _main_en_tmp(datos, tmp_path, monkeypatch):
    csv = tmp_path / "d.csv"
    datos.to_csv(csv, index=False)
    monkeypatch.setattr(config, "DATA_RAW", csv)
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "m" / "modelo.joblib")
    monkeypatch.setattr(config, "MODEL_CARD_PATH", tmp_path / "m" / "model_card.json")
    monkeypatch.setattr(config, "METRICS_PATH", tmp_path / "r" / "evaluacion.json")
    train.main([])
    return csv


def test_main_guarda_modelo_con_card_y_json(datos, tmp_path, monkeypatch):
    csv = _main_en_tmp(datos, tmp_path, monkeypatch)
    guardado = joblib.load(config.MODEL_PATH)
    assert set(guardado) == {"pipeline", "card"}
    card = json.loads(config.MODEL_CARD_PATH.read_text())
    # T128: la huella solo vive en el JSON (el .joblib no puede llevar su propio hash)
    assert card.pop("hash_modelo") == hashlib.sha256(config.MODEL_PATH.read_bytes()).hexdigest()
    assert card == json.loads(json.dumps(guardado["card"]))
    assert card["hash_dataset"] == hashlib.sha256(csv.read_bytes()).hexdigest()
    assert card["features"] == config.FEATURES and config.SENSITIVE_COL not in card["features"]
    assert card["fecha_entrenamiento"].endswith("+00:00")  # UTC
    assert {"metricas_test", "metricas_negocio", "equidad", "criterios_cumplidos",
            "perfil_referencia", "umbral", "version", "algoritmo"} <= card.keys()
    assert json.loads(config.METRICS_PATH.read_text())["umbral"] == card["umbral"]


def test_aprobado_exige_todos_los_criterios_y_no_es_aprobacion_humana(datos, tmp_path, monkeypatch):
    _main_en_tmp(datos, tmp_path, monkeypatch)
    card = json.loads(config.MODEL_CARD_PATH.read_text())
    assert card["aprobado_para_despliegue"] == all(card["criterios_cumplidos"].values())
    assert card["aprobacion"] == {"aprobado_por": None, "fecha": None}


def test_equidad_incumplida_bloquea_la_aprobacion(datos, monkeypatch):
    monkeypatch.setattr(config, "MAX_DIF_RECALL", -1.0)  # imposible de cumplir
    card = train.entrenar(datos, "logreg")["card"]
    assert card["criterios_cumplidos"]["equidad_recall"] is False
    assert card["aprobado_para_despliegue"] is False


def test_perfil_referencia_tiene_deciles_y_frecuencias(datos):
    perfil = train.entrenar(datos, "logreg")["card"]["perfil_referencia"]
    assert set(perfil) == set(config.FEATURES)
    cargo = perfil["cargo_mensual"]
    assert len(cargo["limites"]) == 9 and len(cargo["frecuencias"]) == 10
    assert sum(cargo["frecuencias"]) == pytest.approx(1.0)
    assert sum(perfil["tipo_plan"]["frecuencias"].values()) == pytest.approx(1.0)


# --- 5 criterios, razones y revisión de proxies (T120; FR-018, FR-024, SC-004, SC-010; D1, D3)
CRITERIOS = {"recall", "precision", "precision_top", "roc_auc", "roi",
             "equidad_recall", "ratio_impacto_dispar", "tamano_grupos"}


def test_card_trae_los_criterios_de_la_constitucion_y_de_equidad(datos):
    card = train.entrenar(datos, "logreg")["card"]
    _, te = particionar(datos)
    assert set(card["criterios_cumplidos"]) == CRITERIOS
    assert card["metricas_test"]["precision_top"]["k"] == int(len(te) * config.TOP_EVALUACION)
    assert "roi_estimado" in card["metricas_negocio"]
    assert "ratio_impacto_dispar" in card["equidad"]
    assert card["aprobado_para_despliegue"] == all(card["criterios_cumplidos"].values())
    assert (card["razones_no_aprobado"] == []) == card["aprobado_para_despliegue"]


def test_cada_criterio_incumplido_aparece_en_las_razones(datos, monkeypatch):
    monkeypatch.setattr(config, "MAX_DIF_RECALL", -1.0)
    monkeypatch.setattr(config, "MIN_RATIO_IMPACTO", 2.0)
    monkeypatch.setattr(config, "MIN_ROI", 1e9)
    monkeypatch.setattr(config, "MIN_PRECISION_TOP", 1.1)
    card = train.entrenar(datos, "logreg")["card"]
    texto = " | ".join(card["razones_no_aprobado"])
    for esperado in ("brecha de recall", "impacto dispar", "ROI", "precision en el"):
        assert esperado in texto, esperado
    assert card["aprobado_para_despliegue"] is False


def test_ratio_de_impacto_bajo_bloquea_la_aprobacion(datos, monkeypatch):
    monkeypatch.setattr(config, "MIN_RATIO_IMPACTO", 2.0)
    card = train.entrenar(datos, "logreg")["card"]
    assert card["criterios_cumplidos"]["ratio_impacto_dispar"] is False
    assert card["aprobado_para_despliegue"] is False


def test_grupo_pequeno_bloquea_la_aprobacion(datos, monkeypatch):
    monkeypatch.setattr(config, "MIN_GRUPO_AUDITORIA", 10_000)
    card = train.entrenar(datos, "logreg")["card"]
    assert card["criterios_cumplidos"]["tamano_grupos"] is False and not card["aprobado_para_despliegue"]


def test_revision_de_proxies_compara_con_y_sin_cada_variable(datos):
    rev = train.entrenar(datos, "logreg")["card"]["revision_proxies"]
    assert set(rev) == {"sin_metodo_pago", "sin_tipo_plan", "sin_antiguedad_meses"}
    for nombre, v in rev.items():
        quitada = nombre.removeprefix("sin_")
        assert quitada not in v["features"] and config.SENSITIVE_COL not in v["features"]
        assert set(v["recall_por_grupo"]) == set(config.RANGOS_EDAD)
        assert {"dif_max_recall", "ratio_impacto_dispar", "recall", "umbral"} <= v.keys()
