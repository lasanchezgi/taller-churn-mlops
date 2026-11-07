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
    umbral = train.calibrar_umbral(train.construir_modelo("logreg"), X, y)
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
