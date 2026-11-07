# Quickstart: validación de extremo a extremo

Guía para comprobar que la funcionalidad cumple la spec 002. Describe qué ejecutar y qué resultado
esperar; el detalle de campos está en [data-model.md](data-model.md) y el contrato en
[contracts/openapi.yaml](contracts/openapi.yaml). Los comandos existen cuando se complete la
implementación (`tasks.md`).

## Prerrequisitos

- Python 3.11 o superior y `uv` instalado.
- Desde la raíz del repositorio: `uv sync --extra dev`.
- Sin cuentas, nube ni servicios externos. Docker es opcional.

## 1. Preparar datos y entrenar

```bash
python -m churn.dataset      # fuente de verdad: data/raw/churn_telco.csv (5.000 filas, 25 % de churn aprox.); el generador es solo para demos
python -m churn.train        # regresión logística; escribe modelo, model card (con referencia de PSI y huella)
```

Esperado (FR-018, SC-004, SC-010):
- `models/churn_model.joblib` y `models/model_card.json` existen.
- En el model card: los 5 criterios de FR-018 con su resultado, `razones_no_aprobado`, la lista de `features` sin
  `rango_edad`, y métricas por grupo de edad con la diferencia máxima de recall y el ratio de impacto dispar.
- Si algún criterio falla, el entrenamiento no aborta: el modelo queda con `aprobado_para_despliegue=false` (FR-027).
- Repetir el entrenamiento da exactamente las mismas métricas (semilla fija, FR-016).
- Si la regresión no cumple, `python -m churn.train --algoritmo rf` entrena la alternativa.

## 2. Levantar el servicio

```bash
uv run uvicorn churn.api:app --port 8000
```

## 3. Escenarios de validación

| # | Qué hacer | Resultado esperado | FR / SC |
|---|---|---|---|
| 1 | `GET /health` con modelo cargado | `sano`, la versión, `aprobado_para_despliegue` y `alertas` (con el modelo actual: no aprobado y una alerta) | FR-013, FR-028 |
| 2 | `POST /predict` con un cliente válido | probabilidad 0–1, nivel, recomendación del catálogo, versión, aviso y, si el modelo no está aprobado, `alerta_equidad` | FR-001..005, FR-026, SC-001 |
| 3 | `POST /predict` con `antiguedad_meses` = 121 | error 422 que nombra el campo y el rango 1–120 | FR-006/007, SC-002 |
| 4 | `POST /predict` con `rango_edad` o cualquier campo extra | error 422 que nombra el campo no previsto | FR-007/008, SC-002, SC-006 |
| 5 | `POST /predict` con `reclamos_ult_3m` = 2.5 | error 422 (debe ser entero) | FR-006 |
| 6 | `POST /predict/lote` con 1.000 clientes válidos | 1.000 predicciones en orden y un resumen; en menos de 10 s | FR-009/010, SC-003 |
| 7 | `POST /predict/lote` con 1.001 clientes, con lote vacío y con un cliente inválido en la posición 3 | rechazo en los tres casos; el último indica la posición 3 y el campo | FR-009 |
| 8 | Comparar el resumen con un cálculo manual (cuántos ≥ 0,70 y suma de sus cargos) | coinciden | FR-010, SC-008 |
| 9 | `POST /campana/contactos` con más de 250 clientes en riesgo alto y valores por defecto | exactamente 250 contactos, ordenados por ingreso esperado, `costo_total` = 2.000 | FR-011, SC-007 |
| 10 | Mismo pedido con `presupuesto` = 5 | lista vacía con mensaje claro | FR-011/012 |
| 11 | Mismo pedido con `presupuesto` = 0 | error 422 | FR-012 |
| 12 | `POST /drift` con un lote tomado del conjunto de prueba del CSV | todas las variables `estable` (PSI < 0,10) | FR-014, SC-009 |
| 13 | `POST /drift` con `cargo_mensual` desplazado de forma intencional | esa variable `critico` y recomendación de reentrenar | FR-014, SC-009 |
| 14 | `POST /drift` con 50 clientes | `datos_insuficientes` | FR-014 |
| 15 | Revisar `logs/predicciones.jsonl` tras los pasos anteriores | ningún `id_cliente` en claro; solo el código irreversible | FR-015, SC-005 |
| 16 | Abrir `http://localhost:8000/dashboard` antes y después de puntuar un lote | antes, un mensaje claro de que no hay datos; después, estado, resumen de riesgo y cambio de datos, sin identificadores | FR-019 |
| 17 | Repetir el paso 2 con la misma entrada | misma probabilidad | FR-016 |
| 18 | Detener el servicio, borrar (o alterar) `models/churn_model.joblib` y volver a levantarlo; `GET /health` y `POST /predict` | `no_sano`, y el segundo responde 503 sin predicción | FR-013, FR-021 |
| 19 | `GET /drift` antes y después de un informe | antes, mensaje claro (404); después, el último informe | FR-014 |

## 4. Pruebas automáticas y verificación

```bash
uv run pytest                       # todas las pruebas deben pasar (constitución II)
uv run python scripts/smoke_test.py # verificación rápida del servicio en marcha
```

Esperado: la matriz de trazabilidad FR → prueba de `plan.md` está cubierta y `pytest` termina en verde.

## 5. Opcional: Docker

```bash
docker build -t churn-telco .
docker run --rm -p 8000:8000 churn-telco
```

No es necesario para ningún escenario anterior.

## 6. Criterio de salida a producción (constitución VI)

Solo si: métricas ≥ umbrales, `pytest` en verde, model card con versión y hash, ASUM-DM revisado por
pares y aprobación explícita del dueño del modelo registrada en el model card. Los datos del taller son
sintéticos: no extrapolar los resultados a clientes reales sin revalidar.
