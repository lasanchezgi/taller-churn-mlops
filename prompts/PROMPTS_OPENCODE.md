# Prompts listos para OpenCode (en español)

> **Nota (auditoría, 2026-11-06): IDs de tarea corregidos.** Los IDs `T0xx` de los prompts de abajo no coinciden con `specs/002-campana-retencion-monitoreo/tasks.md`
> (la 001 fue reemplazada por la 002; la 001 no tiene `tasks.md`). Usa esta tabla; el contenido de los prompts no cambia.
>
> | Prompt | ID en el prompt | ID correcto en `tasks.md` | Archivo |
> |---|---|---|---|
> | P3.a dataset | T004 | T009 (pruebas T004) | `src/churn/dataset.py` |
> | P3.b features | T006 | T010 (pruebas T005) | `src/churn/features.py` |
> | P3.d evaluación | T007 | T011 (pruebas T006); **va antes que P3.c** porque `train.py` la importa | `src/churn/evaluate.py` |
> | P3.c entrenamiento | T008 | T015 (pruebas T014) | `src/churn/train.py` |
> | P3.e model card | T008 (repetido) | T015: el model card lo arma `train.py` (no hay `model_card.py`) | `src/churn/train.py` |
> | P3.f API | T010–T013 | T022, T024, T026 (+ `Cliente` y `Prediccion` en `api.py`, `predict.py`) | `src/churn/api.py`, `predict.py` |
> | P3.g pruebas | T014 | T018–T020, T025: **las pruebas van antes** que el código (`tasks.md`) | `tests/` |
> | P3.h README | T024 | T063, T088, T131 | `README.md` |
> | P4.1 health | T018 | T046; el contrato es `estado: sano/no_sano` (no `status ok/degradado`), más `aprobado_para_despliegue` y `alertas` | `src/churn/api.py` |
> | P4.2 logging | T019 | T045, T047; el módulo es `registro.py` con `id_codificado` (no `monitoring.py`) y sin `features` en el log | `src/churn/registro.py` |
> | P4.3 métricas | T020 | T058 | `src/churn/api.py`, `metricas.py` |
> | P4.4 drift | T021 | T051, T055, T108 | `src/churn/drift.py` |
> | P4.5 gobernanza | — | `docs/GOBERNANZA.md` (T126) | `docs/GOBERNANZA.md` |
>
> Otras correcciones: P3.f no devuelve `id_cliente` en `/predict` (FR-011); las rutas `@specs/001-api-churn/...` deben leerse como `@specs/002-campana-retencion-monitoreo/...`.
> Spec Kit: en Claude Code los comandos son `/speckit-*` y en OpenCode `/speckit.*`.

**Cómo usarlos**
- Copia **un** prompt por vez en OpenCode (panel en VS Code o `opencode` en la terminal integrada).
- Con modelos locales de 3B a 7B funcionan mejor los prompts **cortos y con un solo archivo destino**.
- Tras cada respuesta: lee el código, ejecuta el comando de verificación y compáralo con `spec.md`.
- Si el modelo se desvía: escribe `Detente. Relee AGENTS.md y la tarea T0xx. Corrige sólo <archivo>.`
- Para mencionar archivos usa `@ruta/archivo` (p. ej., `@specs/001-api-churn/spec.md`).

---

## Bloque 1 · ASUM-DM (opcional, para pulir el documento)

**P1.1 · Revisar objetivo y KPIs**
```
Lee @business/ASUM-DM.md. Actúa como gerente de retención exigente.
Señala en una tabla qué KPI no tiene fórmula, línea base o meta, y propone la corrección.
No cambies el archivo; sólo responde.
```

**P1.2 · Riesgos**
```
Para el modelo de churn de @business/ASUM-DM.md lista 5 riesgos (sesgo, calidad de datos, drift,
uso indebido, privacidad) con impacto y mitigación concreta. Formato: tabla markdown.
```

---

## Bloque 2 · Spec-Driven Development con Spec Kit

**P2.1 · Constitución**
```
/speckit.constitution Crea los principios del proyecto de churn: 1) todo requisito se rastrea a un KPI de business/ASUM-DM.md; 2) cada requisito tiene una prueba automática y pytest debe pasar; 3) reproducibilidad con semilla fija y sin servicios que requieran cuentas; 4) seguridad y privacidad: validar toda entrada, rechazar campos no previstos, no registrar IDs en claro; 5) explicabilidad y equidad: modelo simple primero, sin atributos sensibles como predictores y auditoría por grupo; 6) gobernanza: versión semántica y model card, nada a producción sin aprobación; 7) supervisión humana: el sistema apoya, no decide. Escribe en español.
```

**P2.2 · Especificación (sólo el QUÉ y el PORQUÉ)**
```
/speckit.specify Como analista de retención, quiero una API que reciba datos del cliente y devuelva probabilidad de churn, nivel de riesgo y recomendación de acción. Datos de entrada: antigüedad en meses, tipo de plan, cargo mensual, reclamos de los últimos 3 meses, uso de datos, método de pago y si renovó contrato. También necesito puntuar lotes mensuales, ver clientes e ingresos en riesgo y a quiénes contactar con un presupuesto de 2.000 USD (8 USD por contacto), saber si el servicio está sano y si los datos cambian frente al entrenamiento. Criterios: recall >= 0,70, precision >= 0,40, ROC-AUC >= 0,75. No uses la edad para predecir. No menciones tecnologías. Escribe en español.
```

**P2.3 · Clarificar**
```
/speckit.clarify Concéntrate en: definición exacta de churn y horizonte, rangos válidos de cada dato, qué hacer con campos no previstos, tamaño máximo de lote y quién define las recomendaciones.
```

**P2.4 · Ejercicio didáctico: detectar solución prematura**
```
Revisa @specs/001-api-churn/spec.md y lista cada frase que mencione una tecnología, librería,
framework, algoritmo o formato de archivo. Para cada una propone una redacción en términos de negocio.
```

**P2.5 · Plan técnico (aquí SÍ va la tecnología)**
```
/speckit.plan Python 3.11+, pandas y numpy para datos, scikit-learn con Pipeline (ColumnTransformer + LogisticRegression, alternativa RandomForest), joblib para serializar modelo y model card JSON, FastAPI con Pydantic v2 para la API (extra="forbid", rangos y Literal), pytest con TestClient, métricas en JSON y logs en JSONL, drift con PSI, dashboard HTML estático sin dependencias. Docker opcional. Sin Kubernetes, sin MLflow, sin servicios en la nube. Estructura tipo Cookiecutter Data Science con código en src/churn/.
```

**P2.6 · Tareas**
```
/speckit.tasks Organiza por historia de usuario, prueba antes que implementación, marca [P] lo paralelizable e indica el archivo destino y el FR o SC que cubre cada tarea.
```

**P2.7 · Checklist**
```
/speckit.checklist Genera un checklist de calidad de requisitos para seguridad de la API, privacidad y equidad.
```

> **Atajo del taller**: si Spec Kit o el modelo local fallan, copia las versiones de referencia:
> `specs/001-api-churn/*.md` y `.specify/memory/constitution.md` vienen en el repositorio solución.

---

## Bloque 3 · Desarrollo con OpenCode + skills ECC + modelo local

**P3.0 · Preparación del agente**
```
Lee @AGENTS.md y @specs/001-api-churn/tasks.md. Carga las skills ml-churn-pipeline y python-testing.
Resume en 5 viñetas qué vas a construir y en qué orden. No escribas código todavía.
```

**P3.a · Dataset sintético (T004)**
```
Tarea T004. Usando la skill ml-churn-pipeline, crea src/churn/dataset.py con una función generar(n=5000, seed=42, escenario="base")
que devuelva un DataFrame con: id_cliente, antiguedad_meses, tipo_plan, cargo_mensual, reclamos_ult_3m, uso_datos_gb,
metodo_pago, renovo_contrato, rango_edad y churn (0/1). El churn debe depender de forma lógica de las variables
(más reclamos y prepago = más churn; renovar y más antigüedad = menos churn) con tasa cercana al 25 %.
Usa numpy.random.default_rng(seed). Agrega un escenario "crisis" con cargos más altos y más reclamos.
Columnas y dominios: @src/churn/config.py. Comentarios breves en español.
```
Verificar: `python -m churn.dataset` → debe imprimir 5000 filas y churn ≈ 25 %.

**P3.b · Preparación de datos (T006)**
```
Tarea T006. Crea src/churn/features.py con: cargar_datos(ruta), validar_calidad(df) que lance DataQualityError
si hay columnas faltantes, nulos, valores fuera de rango o categorías no permitidas; particionar(df) estratificado
con config.SEED; construir_preprocesador() con StandardScaler para numéricas y OneHotEncoder(handle_unknown="ignore")
para categóricas. No uses rango_edad como feature.
```

**P3.c · Entrenamiento baseline (T008)**
```
Tarea T008. Crea src/churn/train.py: Pipeline(preprocesador + LogisticRegression(class_weight="balanced")).
Calibra el umbral con cross_val_predict sobre train: el de mayor precisión con recall >= config.MIN_RECALL.
Opción --algoritmo rf para RandomForest. Ejecutable con python -m churn.train.
```

**P3.d · Evaluación (T007)**
```
Tarea T007. Crea src/churn/evaluate.py con metricas_tecnicas(y, proba, umbral) que devuelva roc_auc, precision,
recall, f1 y matriz de confusión; metricas_negocio(proba, cargo, umbral) con clientes en riesgo, ingresos en riesgo
y clientes priorizados según presupuesto (config.PRESUPUESTO_CAMPANA / config.COSTO_CONTACTO); y
metricas_equidad(y, proba, grupos, umbral) con tasa de selección y recall por grupo y ratio de impacto dispar.
```

**P3.e · Serialización y model card (T008)**
```
En src/churn/train.py guarda con joblib {"pipeline": modelo, "card": card} en models/churn_model.joblib y el card
en models/model_card.json con: version, algoritmo, fecha UTC, hash sha256 del dataset, features, umbral,
métricas de test, métricas de negocio, equidad, criterios cumplidos, aprobado_para_despliegue y perfil de
referencia (deciles y frecuencias) para drift.
```
Verificar: `python -m churn.train` → ROC-AUC ≥ 0,75, recall ≥ 0,70, `aprobado=True`.

**P3.f · API FastAPI (T010–T013)**
```
Carga la skill api-security-review. Tareas T010-T013. Crea src/churn/api.py con FastAPI:
modelo Pydantic Cliente con extra="forbid", rangos con Field(ge, le) y Literal para categorías;
POST /predict que devuelva id_cliente, probabilidad_churn, nivel_riesgo (alto/medio/bajo), recomendacion,
version_modelo y aviso de revisión humana; manejador de RequestValidationError que devuelva 422 con
{"error": "Entrada inválida", "detalle": [{"campo", "mensaje"}]}; 503 si el modelo no cargó; 500 genérico.
Carga el modelo en lifespan. Usa src/churn/predict.py para puntuar.
```
Verificar: `uv run uvicorn churn.api:app --reload` y abrir http://localhost:8000/docs

**P3.g · Pruebas (T014)**
```
Carga la skill python-testing. Tarea T014. Crea tests/test_api.py con TestClient (dentro de with) que pruebe:
caso feliz, cargo negativo (422 y campo cargo_mensual), tipo_plan inválido, campo extra "cedula",
campo faltante, y que un cliente riesgoso tenga mayor probabilidad que uno fiel. Fixtures en tests/conftest.py.
```
Verificar: `pytest` → todo en verde.

**P3.h · README ejecutable (T024)**
```
Carga la skill docs-es. Actualiza README.md con: qué hace el proyecto, instalación para Windows (PowerShell),
macOS y Linux, comandos para generar datos, entrenar, probar, levantar la API y ver el dashboard, salida esperada
de cada comando y una sección de uso responsable.
```

**P3.r · Revisión contra la especificación (después de cada paso)**
```
Carga la skill spec-code-review. Compara el código actual con @specs/001-api-churn/spec.md y
@specs/001-api-churn/tasks.md. Devuelve la matriz requisito | archivo | prueba | estado y la lista de brechas
como tareas nuevas. No modifiques código.
```

**P3.c2 · Convergencia**
```
/speckit.converge
```
Repetir `/speckit.implement` (o los prompts P3.x) y `/speckit.converge` hasta que reporte **Converged**.

---

## Bloque 4 · MLOps mínimo viable

**P4.1 · Health y versión**
```
Carga la skill mlops-architecture. Tarea T018. Agrega GET /health en src/churn/api.py que devuelva status
("ok"/"degradado"), modelo_cargado, version_modelo, aprobado_para_despliegue y error. Agrega su prueba.
```

**P4.2 · Logging estructurado**
```
Tarea T019. Crea src/churn/monitoring.py con una clase Monitor que escriba una línea JSON por predicción en
logs/predicciones.jsonl con ts, id_cliente_hash (sha256 recortado, nunca el ID en claro), features,
probabilidad, nivel, version_modelo y latencia_ms. Prueba que el log no contenga el ID en claro.
```

**P4.3 · Métricas de operación y negocio**
```
Tarea T020. Agrega GET /metrics con: predicciones_totales, errores_totales, distribucion_riesgo, latencia p50/p95,
datos del modelo (versión, umbral, métricas offline) y métricas de negocio (clientes en riesgo, ingresos en riesgo,
clientes priorizados, costo y ROI esperado) sobre las últimas predicciones.
```

**P4.4 · Drift**
```
Tarea T021. Crea src/churn/drift.py con PSI por variable usando los deciles del perfil de referencia del
model card (alerta >= 0.10, crítico >= 0.25) y una función simular("crisis") que compare métricas técnicas
y de negocio entre el dataset base y el escenario crisis y guarde reports/metrics/drift.json.
```
Verificar: `python -m churn.drift --escenario crisis` y `python scripts/simular_trafico.py --escenario crisis`

**P4.5 · Gobernanza**
```
Carga la skill docs-es. Redacta docs/GOBERNANZA.md: quién aprueba un modelo (RACI), qué evidencias se guardan
(model card, evaluacion.json, drift.json, resultados de pytest, spec y tasks), política de versionado semántico
del modelo, disparadores de reentrenamiento y procedimiento de retiro (rollback).
```

---

## Prompts de rescate (modelos locales pequeños)
- `Responde sólo con el contenido completo del archivo <ruta>, sin explicaciones.`
- `El archivo quedó incompleto. Continúa exactamente desde la línea: <última línea>.`
- `Ejecuta pytest y corrige sólo el primer error. Muestra el diff.`
- `No inventes columnas. Usa únicamente las de @src/churn/config.py.`
- `Explica en 5 líneas qué hace @src/churn/<archivo>.py y qué requisito FR cubre.`
