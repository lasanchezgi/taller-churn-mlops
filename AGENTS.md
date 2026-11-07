# Reglas del agente para este repositorio (OpenCode las carga automáticamente)

## Contexto
Proyecto de taller: predicción de churn en telecomunicaciones. Fuente de verdad, en este orden:
1. `business/ASUM-DM.md` (objetivo de negocio, KPIs, criterios de éxito, riesgos).
2. `.specify/memory/constitution.md` (principios no negociables).
3. `specs/002-campana-retencion-monitoreo/spec.md`, `plan.md`, `tasks.md` (reemplaza a `specs/001-api-churn`).

## Reglas
- Responde y comenta el código **en español**, con comentarios breves.
- Antes de escribir código, cita la tarea (`T0xx`) y el requisito (`FR-xxx`) que implementas.
- No inventes columnas: usa sólo las de `src/churn/config.py`.
- Nunca uses `rango_edad` como feature del modelo (sólo para auditar sesgo).
- Toda entrada de la API se valida con Pydantic (rangos y dominios); los errores devuelven 422 con mensaje claro.
- No registres identificadores en claro en los logs: usa un hash.
- Cada cambio de lógica viene con su prueba en `tests/` y `pytest` debe pasar.
- Semilla fija (`config.SEED`) en todo lo aleatorio.
- No agregues dependencias que requieran cuentas, servicios pagos ni Kubernetes. MLflow solo como extra opcional y local (D11): la API y las pruebas no pueden depender de él.
- Si una instrucción contradice la especificación, detente y pregunta.
- Haz cambios pequeños: un archivo o una función por paso.

## Skills disponibles (cárgalas con la herramienta `skill` cuando apliquen)
`ml-churn-pipeline`, `python-testing`, `api-security-review`, `mlops-architecture`, `docs-es`, `spec-code-review`.

## Comandos útiles
- Datos: `python -m churn.dataset` · Entrenar: `python -m churn.train` · Drift: `python -m churn.drift`
- Entorno: `uv sync --extra dev` · API: `uv run uvicorn churn.api:app --reload` · Pruebas: `uv run pytest` · Verificación: `uv run python scripts/smoke_test.py`
