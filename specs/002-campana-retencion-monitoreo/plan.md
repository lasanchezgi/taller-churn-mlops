# Implementation Plan: Riesgo de churn, campaña de retención y monitoreo

**Branch**: `002-campana-retencion-monitoreo` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-campana-retencion-monitoreo/spec.md`

## Summary

Un servicio que puntúa clientes (individual y por lote de hasta 1.000), resume clientes e ingresos en
riesgo, elige a quiénes contactar dentro de 2.000 USD (8 USD por contacto, 250 contactos), informa su
salud y detecta cambios en los datos frente al entrenamiento (PSI), con una vista visual de solo lectura.
El modelo es una regresión logística dentro de un `Pipeline` de scikit-learn (Random Forest solo si la
regresión no cumple los umbrales). `rango_edad` nunca es feature; solo audita el modelo por grupo.
Todo corre en local, con semilla fija, sin cuentas ni servicios de pago.

## Technical Context

**Language/Version**: Python 3.11+ (`requires-python = ">=3.11"` ya declarado en `pyproject.toml`)

**Primary Dependencies**: numpy, pandas, scikit-learn (Pipeline + ColumnTransformer + LogisticRegression; alternativa RandomForest), joblib, FastAPI, Pydantic v2, uvicorn. Desarrollo: pytest, httpx (requerido por `TestClient`). Todas ya están en `pyproject.toml`. Única adición (D11): un extra **opcional** `mlflow` para el seguimiento de experimentos; el servicio, el entrenamiento y las pruebas funcionan sin él.

**Storage**: archivos locales (con el extra opcional, además `mlflow.db` y `mlruns/`, solo locales). Datos en CSV (`data/raw/churn_telco.csv`), modelo en `models/churn_model.joblib`, model card en `models/model_card.json`, métricas y estado del monitoreo en JSON bajo `reports/metrics/`, registro de predicciones en JSONL (`logs/predicciones.jsonl`). Sin base de datos.

**Testing**: pytest con `TestClient` de FastAPI, `testpaths = ["tests"]`. Cada FR tiene al menos una prueba (constitución II).

**Target Platform**: macOS, Linux y Windows en local. Docker es opcional (no requerido para ejecutar ni probar).

**Project Type**: servicio web (API de solo lectura/consulta) más tuberías de entrenamiento por línea de comandos; estructura tipo Cookiecutter Data Science con el código en `src/churn/`.

**Performance Goals**: predicción individual < 1 s; lote de 1.000 con resumen y lista de contacto < 10 s (SC-003).

**Constraints**: semilla fija `config.SEED`; sin Kubernetes, nube ni servicios que requieran cuentas (el seguimiento de experimentos es opcional y local, D11); entrada validada con `extra="forbid"`; ningún identificador en claro en logs; cambios pequeños (un archivo o función por paso).

**Scale/Scope**: 5.000 clientes de entrenamiento (sintéticos), 7 variables de entrada, lotes de hasta 1.000, 250 contactos al mes, un solo modelo servido a la vez.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento en este plan | Estado |
|---|---|---|
| I. Trazabilidad a los KPI | Cada FR de la spec nombra su KPI; `tasks.md` citará `T0xx` y `FR-xxx`. Umbrales de promoción tomados de `config.py` (alineado con el ASUM-DM). | Pasa |
| II. Pruebas y pytest en verde | Mapa FR → archivo de prueba en este plan (ver "Trazabilidad de pruebas"). | Pasa |
| III. Reproducibilidad y autonomía | `config.SEED`; `Pipeline` ajustado solo con entrenamiento; solo bibliotecas locales y abiertas; Docker opcional sin cuenta. | Pasa |
| IV. Seguridad y privacidad | `extra="forbid"`, rangos y `Literal`; error de validación con mensaje que nombra el campo; hash con sal de los identificadores en el JSONL. | Pasa |
| V. Explicabilidad y equidad | Regresión logística primero, RF solo si no cumple; auditoría por `rango_edad` en cada entrenamiento y en el model card. | Pasa |
| VI. Gobernanza y versionado | Model card con versión semántica, métricas, hash y fecha; sin salida a producción sin aprobación del dueño del modelo (paso manual documentado); `aprobado_para_despliegue` es solo la compuerta técnica, no sustituye la firma. | Pasa |
| VII. Supervisión humana | Aviso en cada respuesta de predicción y de lista de contacto; catálogo fijo de recomendaciones; la vista visual es de solo lectura. | Pasa |

Sin violaciones: no se requiere la tabla de Complexity Tracking.

**Re-evaluación tras el diseño (Fase 1)**: los siete principios siguen cumpliéndose. Dos riesgos de diseño quedaron como decisiones abiertas para el dueño del proyecto (ver `research.md`, D-09 y D-10), sin violar la constitución.

## Decisiones de la auditoría (2026-11-06)

Registradas en [docs/DECISIONES.md](../../docs/DECISIONES.md) (D1–D11 e interpretaciones I-1 a I-12). Efectos en este plan: los nombres del código mandan (`predict.py`; `Cliente` y `Prediccion` en `api.py`; sin `schemas.py` ni `model_card.py`); la compuerta de promoción usa los 5 criterios de la constitución I; un modelo no aprobado se sirve con alerta de equidad; la referencia de PSI vive en el model card y sale del conjunto de entrenamiento del CSV; la huella del modelo va en `models/model_card.json`; la regresión logística frente al Random Forest se compara solo como intento de mitigación (`mitigacion.py`), sin cambiar el modelo servido. D11 añade una capa opcional de seguimiento (`seguimiento.py`, `--mlflow` en `train.py` y `drift.py`, `scripts/promover_modelo.py`): la API sigue cargando el `.joblib` con su huella y no la conoce.

## Project Structure

### Documentation (this feature)

```text
specs/002-campana-retencion-monitoreo/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, campos y reglas
├── quickstart.md        # Fase 1: guía de validación de extremo a extremo
├── contracts/
│   └── openapi.yaml     # Fase 1: contrato de la interfaz del servicio
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks; NO lo crea este comando)
```

### Source Code (repository root)

Estructura tipo Cookiecutter Data Science adaptada. Lo que ya existe se marca (existe); el resto se crea en la implementación.

```text
data/
├── raw/churn_telco.csv              # (existe) datos de origen
├── processed/                       # dataset procesado y distribución de referencia para PSI
└── drift/                           # lotes simulados para pruebas de cambio de datos
models/                              # churn_model.joblib y model_card.json
reports/
├── metrics/                         # evaluacion.json, drift.json, ultimo_lote.json
└── figures/
logs/                                # predicciones.jsonl
dashboard/
└── index.html                       # (existe) vista estática de solo lectura, sin dependencias
src/churn/
├── __init__.py                      # (existe)
├── config.py                        # (existe) se amplía: límites de entrada, tamaño de lote, rutas nuevas
├── dataset.py                       # generar/validar el CSV y la partición
├── features.py                      # Pipeline: ColumnTransformer + clasificador
├── train.py                         # entrenar, evaluar, elegir modelo, guardar con model card
├── evaluate.py                      # recall, precision, ROC-AUC, precision@k, ROI estimado, auditoría por grupo
├── recomendaciones.py               # catálogo fijo (una acción por nivel de riesgo)
├── predict.py                       # cargar modelo (con huella), predecir, nivel de riesgo, recomendación
├── campana.py                       # resumen de riesgo y selección de contactos por ingreso esperado
├── drift.py                         # PSI por variable y clasificación
├── registro.py                      # hash con sal y escritura JSONL
├── limitador.py                     # límite de solicitudes por IP, en memoria
├── mitigacion.py                    # intento único de mitigación de equidad (LR vs RF, proxies)
├── seguimiento.py                   # (opcional, D11) registra corridas de entrenamiento y drift; importa el extra solo al usarlo
└── api.py                           # rutas y modelos de entrada/salida (Cliente, Prediccion, ...)
tests/
├── unit/                            # cliente, predict, campana, drift, registro, evaluate, limitador, mitigacion
├── integration/                     # rutas con TestClient y entrenamiento de extremo a extremo
└── conftest.py                      # modelo de prueba pequeño y entradas de ejemplo
scripts/                             # (existe) smoke_test.py, simular_trafico.py; promover_modelo.py (opcional, D11)
Dockerfile                           # opcional; no es requisito de ningún FR
```

**Structure Decision**: proyecto único (servicio + tuberías de ML en el mismo paquete `src/churn/`), siguiendo la estructura que ya usa el repositorio (`config.py`, `Makefile`, `tareas.py`). No se separan backend y frontend: la vista es un archivo HTML estático servido por el mismo servicio que consume los endpoints de lectura. Un módulo por responsabilidad para respetar "un archivo o una función por paso".

### Trazabilidad de pruebas (FR → prueba)

| FR | Prueba prevista |
|---|---|
| FR-001, FR-002, FR-004 | `tests/integration/test_api_predict.py` (respuesta completa, umbral 0,70 en el límite) |
| FR-003 | `tests/unit/test_recomendaciones.py` (una entrada por nivel; sin textos prohibidos) |
| FR-005, FR-017 | `tests/integration/test_api_predict.py`, `test_api_campana.py` (aviso presente; sin rutas que escriban) |
| FR-006, FR-007, FR-008 | `tests/unit/test_cliente.py` (límites, tipos, categorías, campo extra, edad rechazada) |
| FR-009 | `tests/integration/test_api_lote.py` (1.000 ok, 1.001 y vacío rechazados, posición del inválido) |
| FR-010 | `tests/unit/test_campana.py` (resumen vs cálculo manual) |
| FR-011, FR-012 | `tests/unit/test_campana.py` (250 por defecto, desempate estable, presupuesto no positivo) |
| FR-013 | `tests/integration/test_api_salud.py` (sano, modelo ausente) |
| FR-014 | `tests/unit/test_drift.py` (estable, alerta, crítico, lote pequeño) |
| FR-015 | `tests/unit/test_registro.py` (ningún ID en claro en el JSONL) |
| FR-016 | `tests/unit/test_predict.py`, `test_train.py` (misma entrada, misma salida; semilla fija) |
| FR-018 | `tests/unit/test_evaluate.py`, `tests/integration/test_train.py` (5 criterios; métricas por grupo de edad presentes) |
| FR-019 | `tests/integration/test_api_vista.py` (con y sin lote; sin identificadores) |
| FR-014 (consulta) | `tests/integration/test_api_drift.py` (último informe; sin informe) |
| FR-020 | `tests/unit/test_limitador.py` (solicitud 61 por minuto rechazada) |
| FR-021 | `tests/unit/test_integridad_modelo.py` (huella distinta, `no_sano`) |
| FR-022 | `tests/integration/test_api_errores.py` (sin trazas, rutas ni identificador) |
| FR-023 | `tests/unit/test_registro_campos.py` (cinco campos; retención de 90 días) |
| FR-024, FR-025 | `tests/unit/test_equidad.py` (revisión de proxies, reparto por grupo, regla de no promoción); FR-025 es un procedimiento documentado en `docs/AUDITORIA_EQUIDAD.md` |
| FR-026, FR-028 | `tests/integration/test_api_predict.py`, `test_api_salud.py` (alerta de equidad y `alertas` con modelo no aprobado; ausentes si está aprobado) |
| FR-027 | `tests/integration/test_train_umbral.py` (camino con umbral viable y camino sin umbral viable; no aborta) |
| FR-029 | `tests/integration/test_train_mlflow.py` (sin la opción no se crea nada; con ella hay una corrida con métricas técnicas, de negocio y de equidad y la etiqueta de aprobación), `tests/unit/test_seguimiento.py` (ejemplo de entrada sin identificador ni edad; mensaje claro si falta el extra) |
| FR-030 | `tests/integration/test_promover_modelo.py` (no aprobado sin forzar: falla y no asigna; aprobado: asigna; forzar sin motivo falla; forzar con motivo lo deja registrado; el entrenamiento nunca asigna producción) |
| FR-031 | `tests/integration/test_drift_mlflow.py` (corrida con el PSI de cada variable y el informe) |

## Complexity Tracking

Sin violaciones de la constitución; no aplica.
