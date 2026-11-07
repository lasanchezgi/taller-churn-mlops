"""Pruebas de churn.drift (T051; FR-014, SC-009)."""
import json

import numpy as np
import pytest

from churn import config, drift
from churn.dataset import generar
from churn.predict import cargar_modelo


@pytest.fixture(scope="module")
def ref(ruta_modelo):
    return cargar_modelo(ruta_modelo)["card"]["perfil_referencia"]


def test_psi_calculado_a_mano():
    # (0.5-0.4)·ln(0.5/0.4) + (0.5-0.6)·ln(0.5/0.6)
    esperado = 0.1 * np.log(1.25) + (-0.1) * np.log(0.5 / 0.6)
    assert drift.psi([0.4, 0.6], [0.5, 0.5]) == pytest.approx(esperado)
    assert drift.psi([0.3, 0.7], [0.3, 0.7]) == 0


def test_psi_con_intervalo_vacio_es_finito():
    assert np.isfinite(drift.psi([0.5, 0.5], [1.0, 0.0]))


@pytest.mark.parametrize("valor,nivel", [(0.0999, "estable"), (0.10, "alerta"),
                                         (0.2499, "alerta"), (0.25, "critico")])
def test_umbrales_de_clasificacion(valor, nivel):
    assert drift.clasificar(valor) == nivel


def test_lote_igual_al_entrenamiento_es_estable(ref):
    r = drift.informe(generar(3000, seed=config.SEED + 5), ref)
    assert r["estado_general"] == "estable"
    assert [v["nombre"] for v in r["variables"]] == config.FEATURES


def test_variable_desplazada_es_critica(ref):
    df = generar(3000, seed=config.SEED + 5)
    df["cargo_mensual"] = df["cargo_mensual"] * 1.6
    r = drift.informe(df, ref)
    por = {v["nombre"]: v["nivel"] for v in r["variables"]}
    assert por["cargo_mensual"] == "critico" and r["estado_general"] == "critico"
    assert r["recomendacion"] == "evaluar reentrenamiento"


def test_categoria_nueva_cuenta_como_cambio(ref):
    df = generar(1000, seed=1)
    df["metodo_pago"] = "criptomoneda"
    assert drift.informe(df, ref)["variables"][5]["nivel"] == "critico"


def test_lote_pequeno_da_datos_insuficientes(ref):
    assert drift.informe(generar(50), ref)["estado_general"] == "datos_insuficientes"


def test_simular_crisis_guarda_el_reporte(ruta_modelo, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", ruta_modelo)
    salida = tmp_path / "drift.json"
    r = drift.simular("crisis", salida, df=generar(1500))  # mismos datos con que se entrenó el modelo de prueba
    g = json.loads(salida.read_text())
    assert g == json.loads(json.dumps(r))
    assert g["estado_general"] == "critico"
    s = g["simulacion"]
    assert {"base", "crisis", "delta"} <= s.keys() and s["base"]["informe"]["estado_general"] == "estable"
    assert s["crisis"]["negocio"]["ingresos_6_meses_en_riesgo"] > s["base"]["negocio"]["ingresos_6_meses_en_riesgo"]
