"""dashboard/index.html es de solo lectura, sin recursos externos y sin HTML dinámico (T057; FR-019, FR-017)."""
import re

from churn import config

HTML = config.DASHBOARD_PATH.read_text(encoding="utf-8")


def test_sin_scripts_ni_estilos_externos():
    assert not re.search(r"<script[^>]+src=", HTML) and "<link" not in HTML
    assert "http://" not in HTML.replace("http://www.w3.org", "") and "https://" not in HTML


def test_sin_formularios_ni_envio_de_datos():
    assert "<form" not in HTML and "<input" not in HTML
    assert not re.search(r"method\s*:\s*[\"']?(POST|PUT|PATCH|DELETE)", HTML, re.I)


def test_solo_consulta_health_y_metrics():
    assert set(re.findall(r"fetch\(\s*[\"']([^\"']+)[\"']", HTML)) == {"/health", "/metrics"}


def test_inserta_texto_sin_interpretarlo_como_html():
    assert "innerHTML" not in HTML and "insertAdjacentHTML" not in HTML and "document.write" not in HTML
    assert "textContent" in HTML


def test_muestra_mensaje_claro_sin_datos():
    assert "Aún no se ha puntuado un lote" in HTML
