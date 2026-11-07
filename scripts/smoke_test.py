"""Smoke test del entorno del taller. Uso: python scripts/smoke_test.py [--sin-ia]

Verifica herramientas, Ollama, modelo local, dependencias Python y la API de punta a punta.
Sale con código 0 si todo lo obligatorio está OK.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import os
import tempfile
import urllib.request
from pathlib import Path

os.system("")  # habilita colores ANSI en la consola de Windows

OK, WARN, FAIL = "\033[32m[OK]\033[0m", "\033[33m[AVISO]\033[0m", "\033[31m[FALLA]\033[0m"
MODELOS_ESPERADOS = ("taller-coder", "qwen2.5-coder")
fallas = 0


def check(nombre: str, ok: bool, detalle: str = "", obligatorio: bool = True) -> None:
    global fallas
    marca = OK if ok else (FAIL if obligatorio else WARN)
    if not ok and obligatorio:
        fallas += 1
    print(f"{marca} {nombre} {detalle}")


def version(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
    except Exception:
        return ""


CLIENTE_EJEMPLO = {"antiguedad_meses": 6, "tipo_plan": "prepago", "cargo_mensual": 45.5, "reclamos_ult_3m": 3,
                   "uso_datos_gb": 2.1, "metodo_pago": "efectivo", "renovo_contrato": "no"}


def verificar_api(c) -> list[tuple[str, bool, str]]:
    """Comprueba /health (contrato del spec: estado == "sano") y /predict; devuelve (nombre, ok, detalle)."""
    h = c.get("/health").json()
    p = c.post("/predict", json=CLIENTE_EJEMPLO).json()
    return [
        ("API /health", h.get("estado") == "sano", f"estado={h.get('estado')} modelo v{h.get('version_modelo')}"),
        ("API /predict", "probabilidad_churn" in p, f"p={p.get('probabilidad_churn')} riesgo={p.get('nivel_riesgo')}"),
    ]


def verificar_rutas(c, clientes: list[dict]) -> list[tuple[str, bool, str]]:
    """Lote, campaña, cambio de datos y panel (T062); `clientes` son al menos 100 filas válidas."""
    lote = c.post("/predict/lote", json={"clientes": clientes}).json()
    camp = c.post("/campana/contactos", json={"clientes": clientes}).json()
    drift = c.post("/drift", json={"clientes": clientes}).json()
    panel = c.get("/dashboard")
    return [
        ("API /predict/lote", len(lote.get("predicciones", [])) == len(clientes), f"{len(clientes)} clientes"),
        ("API /campana/contactos", "contactos" in camp, f"{len(camp.get('contactos', []))} contactos"),
        ("API /drift", "estado_general" in drift, f"estado={drift.get('estado_general')}"),
        ("API /dashboard", panel.status_code == 200 and "<html" in panel.text.lower(), f"HTTP {panel.status_code}"),
    ]


def main() -> None:
    sin_ia = "--sin-ia" in sys.argv
    print("== Herramientas ==")
    check("Python >= 3.11", sys.version_info >= (3, 11), sys.version.split()[0])
    for exe, args, oblig in [("git", ["--version"], True), ("node", ["--version"], False),
                             ("code", ["--version"], False), ("uv", ["--version"], not sin_ia),
                             ("specify", ["--help"], not sin_ia), ("opencode", ["--version"], not sin_ia),
                             ("ollama", ["--version"], not sin_ia)]:
        ruta = shutil.which(exe)
        check(exe, bool(ruta), version([exe, *args]) if ruta and exe != "specify" else (ruta or "no encontrado"), oblig)

    if not sin_ia:
        print("\n== Ollama (http://localhost:11434) ==")
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
                modelos = [m["name"] for m in json.load(r).get("models", [])]
            check("Servidor Ollama activo", True)
            hay = [m for m in modelos if m.startswith(MODELOS_ESPERADOS)]
            check("Modelo de código descargado", bool(hay), ", ".join(hay) or f"disponibles: {modelos}")
        except Exception as exc:
            check("Servidor Ollama activo", False, f"({exc}). Ejecute: ollama serve")

    print("\n== Python: dependencias y pipeline ==")
    try:
        import fastapi, pandas, sklearn  # noqa: F401
        check("Dependencias (pandas, scikit-learn, fastapi)", True)
    except ImportError as exc:
        check("Dependencias", False, f"{exc}. Ejecute: uv sync --extra dev")
        return resumen()

    try:
        import churn.dataset  # noqa: F401
        import churn.api  # noqa: F401
    except ImportError:
        check("Código del pipeline", False, "aún no generado (normal en el repo alumno antes del Bloque 3)", obligatorio=False)
        return resumen()

    try:
        from churn import config
        from churn.features import cargar_datos
        if not config.DATA_RAW.exists():
            from churn.dataset import generar
            config.DATA_RAW.parent.mkdir(parents=True, exist_ok=True)
            generar().to_csv(config.DATA_RAW, index=False)
        check("Dataset", True, str(config.DATA_RAW.relative_to(config.ROOT)))
        if not config.MODEL_PATH.exists():
            from churn.train import entrenar, guardar_modelo
            res = entrenar(cargar_datos(config.DATA_RAW))
            guardar_modelo(res, config.MODEL_PATH, config.MODEL_CARD_PATH)  # con huella (FR-021)
        from fastapi.testclient import TestClient
        from churn.api import app
        # La verificación no ensucia reports/ ni logs/ del proyecto
        tmp = Path(tempfile.mkdtemp(prefix="smoke_churn_"))
        config.DRIFT_REPORT_PATH, config.ULTIMO_LOTE_PATH = tmp / "drift.json", tmp / "ultimo_lote.json"
        config.PREDICTIONS_LOG = tmp / "predicciones.jsonl"
        with TestClient(app) as c:
            for nombre, ok, detalle in verificar_api(c):
                check(nombre, ok, detalle)
            muestra = cargar_datos(config.DATA_RAW)[config.FEATURES].head(120).to_dict(orient="records")
            for nombre, ok, detalle in verificar_rutas(c, muestra):
                check(nombre, ok, detalle)
    except Exception as exc:
        check("Pipeline de punta a punta", False, repr(exc))
    resumen()


def resumen() -> None:
    print("\n" + ("Todo listo para el taller." if fallas == 0 else f"{fallas} verificación(es) obligatoria(s) fallaron. Ver docs/PLAN_B.md"))
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
