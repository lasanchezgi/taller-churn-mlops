"""Atajos multiplataforma (equivalente al Makefile, funciona también en Windows).

Uso: python tareas.py <tarea>
Tareas: datos, entrenar, entrenar-rf, probar, api, trafico, drift, smoke, todo, limpiar, mlflow-ui (opcional)
"""
import shutil
import subprocess
import sys
from pathlib import Path

PY = sys.executable
TAREAS = {
    "datos": [[PY, "-m", "churn.dataset"]],
    "entrenar": [[PY, "-m", "churn.train"]],
    "entrenar-rf": [[PY, "-m", "churn.train", "--algoritmo", "rf"]],
    "probar": [[PY, "-m", "pytest"]],
    "api": [[PY, "-m", "uvicorn", "churn.api:app", "--reload", "--port", "8000"]],
    "trafico": [[PY, "scripts/simular_trafico.py"], [PY, "scripts/simular_trafico.py", "--escenario", "crisis", "--n", "500"]],
    "drift": [[PY, "-m", "churn.drift", "--escenario", "crisis"]],
    "smoke": [[PY, "scripts/smoke_test.py"]],
    "mlflow-ui": [[PY, "-m", "mlflow", "ui", "--backend-store-uri", "sqlite:///mlflow.db"]],  # D11, requiere el extra
}
TAREAS["todo"] = TAREAS["datos"] + TAREAS["entrenar"] + TAREAS["probar"] + TAREAS["drift"]


def limpiar() -> None:
    # Borra artefactos generados (se pueden regenerar de forma determinista)
    for p in ["logs/predicciones.jsonl", "reports/metrics/drift.json", ".pytest_cache"]:
        ruta = Path(p)
        shutil.rmtree(ruta) if ruta.is_dir() else ruta.unlink(missing_ok=True)
    print("[ok] artefactos temporales eliminados")


if __name__ == "__main__":
    tarea = sys.argv[1] if len(sys.argv) > 1 else ""
    if tarea == "limpiar":
        limpiar()
    elif tarea in TAREAS:
        for cmd in TAREAS[tarea]:
            print("$", " ".join(cmd[1:] if cmd[0] == PY else cmd))
            if subprocess.call(cmd) != 0:
                sys.exit(1)
    else:
        print(__doc__)
        sys.exit(1)
