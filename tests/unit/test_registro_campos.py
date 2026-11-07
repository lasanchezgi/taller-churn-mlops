"""Campos y retención del registro (T072, T081; FR-023)."""
import json
from datetime import datetime, timedelta, timezone

from churn import config
from churn.registro import Registro

CAMPOS = {"fecha", "id_codificado", "probabilidad_churn", "nivel_riesgo", "version_modelo"}


def _linea(dias_atras: float, marca="x") -> str:
    fecha = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return json.dumps({"fecha": fecha.isoformat(), "id_codificado": marca, "probabilidad_churn": 0.5,
                       "nivel_riesgo": "medio", "version_modelo": "1.0.0"})


def _marcas(ruta):
    return [json.loads(x)["id_codificado"] for x in ruta.read_text().splitlines()]


def test_cada_linea_trae_solo_los_cinco_campos(tmp_path):
    reg = Registro(tmp_path / "p.jsonl", sal="s")
    reg.registrar("C1", 0.8, "alto", "1.0.0")
    reg.registrar(None, 0.2, "bajo", "1.0.0")
    for x in reg.ruta.read_text().splitlines():
        assert set(json.loads(x)) == CAMPOS


def test_retencion_por_defecto_es_90_dias():
    assert config.RETENCION_REGISTRO_DIAS == 90


def test_al_iniciar_elimina_lineas_de_mas_de_90_dias(tmp_path):
    ruta = tmp_path / "p.jsonl"
    ruta.write_text("\n".join([_linea(91, "vieja"), _linea(89, "reciente"), _linea(200, "muyvieja")]) + "\n")
    Registro(ruta, sal="s")
    assert _marcas(ruta) == ["reciente"]


def test_al_registrar_tambien_purga_pasada_una_hora(tmp_path):
    ruta = tmp_path / "p.jsonl"
    reg = Registro(ruta, sal="s")
    ruta.write_text(_linea(120, "vieja") + "\n")
    reg._ultima_purga -= 3601  # simula que pasó más de una hora
    reg.registrar("C1", 0.8, "alto", "1.0.0")
    marcas = _marcas(ruta)
    assert "vieja" not in marcas and len(marcas) == 1


def test_lineas_ilegibles_no_rompen_la_purga(tmp_path):
    ruta = tmp_path / "p.jsonl"
    ruta.write_text("no es json\n" + _linea(1, "ok") + "\n")
    Registro(ruta, sal="s")
    assert "ok" in ruta.read_text() and "no es json" in ruta.read_text()
