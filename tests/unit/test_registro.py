"""Pruebas de churn.registro (T045; FR-015, FR-023, SC-005)."""
import json
import logging

from churn.registro import Registro, SAL_ENV

ID = "C4200123"


def _reg(tmp_path, sal="sal-de-prueba"):
    return Registro(tmp_path / "logs" / "predicciones.jsonl", sal=sal)


def _lineas(reg):
    return [json.loads(x) for x in reg.ruta.read_text().splitlines()]


def test_el_log_no_contiene_el_id_en_claro(tmp_path):
    reg = _reg(tmp_path)
    reg.registrar(ID, 0.81, "alto", "1.0.0", 3.2)
    assert ID not in reg.ruta.read_text()


def test_una_linea_json_por_prediccion_con_los_campos_esperados(tmp_path):
    reg = _reg(tmp_path)
    reg.registrar(ID, 0.81, "alto", "1.0.0", 3.2)
    reg.registrar(None, 0.2, "bajo", "1.0.0", 1.0)
    lineas = _lineas(reg)
    assert len(lineas) == 2
    assert set(lineas[0]) == {"fecha", "id_codificado", "probabilidad_churn", "nivel_riesgo",
                              "version_modelo", "latencia_ms"}
    assert lineas[0]["fecha"].endswith("+00:00") and lineas[0]["latencia_ms"] == 3.2


def test_codigo_es_sha256_truncado_estable_y_distinto_por_id(tmp_path):
    reg = _reg(tmp_path)
    a = reg.codificar(ID)
    assert len(a) == 16 and int(a, 16) >= 0
    assert a == reg.codificar(ID) != reg.codificar("C4200124")


def test_la_sal_cambia_el_codigo(tmp_path):
    assert _reg(tmp_path, "uno").codificar(ID) != _reg(tmp_path, "dos").codificar(ID)


def test_sin_id_se_registra_null(tmp_path):
    reg = _reg(tmp_path)
    reg.registrar(None, 0.5, "medio", "1.0.0", 1.0)
    assert _lineas(reg)[0]["id_codificado"] is None


def test_sin_sal_avisa_y_usa_la_de_desarrollo(tmp_path, monkeypatch, caplog):
    monkeypatch.delenv(SAL_ENV, raising=False)
    with caplog.at_level(logging.WARNING, logger="churn.registro"):
        reg = Registro(tmp_path / "p.jsonl")
    assert SAL_ENV in caplog.text and reg.codificar(ID)


def test_la_sal_viene_de_la_variable_de_entorno(tmp_path, monkeypatch):
    monkeypatch.setenv(SAL_ENV, "secreto")
    assert Registro(tmp_path / "p.jsonl").codificar(ID) == Registro(tmp_path / "q.jsonl", sal="secreto").codificar(ID)
