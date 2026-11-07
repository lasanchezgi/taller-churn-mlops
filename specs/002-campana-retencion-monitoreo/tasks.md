---

description: "Lista de tareas: riesgo de churn, campaña de retención y monitoreo"
---

# Tasks: Riesgo de churn, campaña de retención y monitoreo

**Input**: documentos de diseño en `specs/002-campana-retencion-monitoreo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: se piden de forma explícita (constitución II: cada requisito tiene prueba automática y `pytest` en verde). En cada fase las pruebas van **antes** que la implementación y MUST fallar al escribirlas.

**Organization**: las tareas se agrupan por historia de usuario (US1–US7, numeradas como en la spec). FR-018 y FR-019 no pertenecen a ninguna historia de la spec: FR-018 se cubre en la fase fundacional (el modelo es la base de todo) y FR-019 en la Fase 10 (la vista depende de US4, US6 y US7).

## Format: `- [ ] T### [P?] [US#?] Descripción con archivo destino (FR/SC que cubre)`

- **[P]**: se puede ejecutar en paralelo (archivos distintos y sin depender de tareas incompletas).
- **[US#]**: historia de usuario a la que pertenece (solo en las fases de historia).
- Antes de escribir código se cita la tarea (`T0xx`) y el requisito (`FR-xxx`) en el comentario del archivo, como exige `AGENTS.md`. Comentarios breves y en español.
- Rutas relativas a la raíz del repositorio; el código vive en `src/churn/`.

## Path Conventions

Proyecto único (ver `plan.md`): `src/churn/`, `tests/unit/`, `tests/integration/`, `models/`, `reports/metrics/`, `logs/`, `dashboard/`.

---

## Phase 1: Setup

**Purpose**: estructura y constantes compartidas.

- [ ] T001 Crear las carpetas `tests/unit/`, `tests/integration/` y `reports/metrics/` si faltan, y comprobar que `uv sync --extra dev` instala sin errores (plan: estructura)
- [ ] T002 [P] Escribir `tests/unit/test_config.py`: las `FEATURES` no contienen `rango_edad`, `id_cliente`, `periodo` ni `churn`; existen las constantes nuevas `LOTE_MAX` = 1000, `CARGO_MIN` = 10, `CARGO_MAX` = 1000, `USO_DATOS_MAX` = 1000, `MIN_FILAS_DRIFT` = 100, `TOP_EVALUACION` = 0.05, `MAX_DIF_RECALL` = 0.05 (FR-006, FR-008, FR-009, SC-010)
- [ ] T003 Ampliar `src/churn/config.py` (tras T002) con esas constantes más `ULTIMO_LOTE_PATH` (`reports/metrics/ultimo_lote.json`), `AVISO_USO_RESPONSABLE`, `HASH_SAL_ENV` = `"CHURN_HASH_SALT"` y `UMBRAL_RIESGO_MEDIO` = 0.50; no tocar las existentes. La referencia de drift vive en el model card (`perfil_referencia`), no en un archivo aparte (D6, I-11). Las constantes de D1, D3 y D5 las añade T104 (FR-005, FR-006, FR-009, FR-014)

---

## Phase 2: Foundational (modelo entrenable y validación de entrada)

**Purpose**: lo que bloquea a todas las historias: datos validados, `Pipeline`, evaluación, model card, entrenamiento y el esquema de entrada.

**⚠️ CRITICAL**: ninguna historia empieza hasta cerrar esta fase.

### Pruebas primero (deben fallar)

- [x] T004 [P] Escribir `tests/unit/test_dataset.py`: sin nulos, `id_cliente` único, valores dentro de los dominios de `config.py`, prevalencia del objetivo entre 20 % y 30 %, y la misma semilla genera el mismo CSV (ASUM-DM §3; FR-016)
- [ ] T005 [P] Escribir `tests/unit/test_features.py`: el `ColumnTransformer` usa exactamente `config.FEATURES` (4 numéricas con escalado estándar, 3 categóricas con one-hot); falla si se le pasa `rango_edad`; el ajuste usa solo datos de entrenamiento (FR-008, FR-016)
- [ ] T006 [P] Escribir `tests/unit/test_evaluate.py`: recall, precision y ROC-AUC contra valores calculados a mano; precision en el `TOP_EVALUACION` (5 %) de mayor riesgo; recall y precision por grupo de `rango_edad`; diferencia máxima de recall entre grupos (FR-018, SC-004, SC-010)
- [ ] T007 [P] ~~Escribir `tests/unit/test_model_card.py`~~ **Sustituida (D7, I-9)**: el model card lo arma `train.py`; sus campos (versión MAJOR.MINOR.PATCH, algoritmo, fecha, semilla, umbral, métricas, equidad, `features` sin `rango_edad`, `hash_modelo`, `aprobacion` vacía) se prueban en `tests/integration/test_train.py` (T014, T120, T128) (FR-004, FR-018)
- [ ] T008 [P] Escribir `tests/unit/test_cliente.py` para `Cliente`: acepta los límites (antigüedad 1 y 120, reclamos 0 y 6, cargo 10 y 1000, uso 0 y 1000) y rechaza 0 y 121, 7, 9.99 y 1000.01, -0.1 y 1000.1; rechaza decimales en antigüedad y reclamos, nulos, categorías fuera de dominio, campos faltantes y cualquier campo extra incluido `rango_edad`; `id_cliente` opcional de hasta 64 caracteres (FR-006, FR-007, FR-008, SC-002, SC-006)

### Implementación

- [x] T009 [P] Implementar `src/churn/dataset.py`: generar el CSV con `config.SEED` y validar esquema, dominios, nulos y duplicados; ejecutable con `python -m churn.dataset` (FR-016; ASUM-DM §3)
- [ ] T010 [P] Implementar `src/churn/features.py`: `Pipeline` con `ColumnTransformer` (escalado estándar en `NUMERIC_FEATURES`, one-hot en `CATEGORICAL_FEATURES`) y `LogisticRegression(random_state=config.SEED)`; fábrica alternativa con `RandomForestClassifier` (FR-008, FR-016)
- [ ] T011 [P] Implementar `src/churn/evaluate.py`: métricas globales, precision en el 5 % de mayor riesgo (D-10 resuelta: k = 5 % del conjunto evaluado) y auditoría por `rango_edad` con la diferencia máxima de recall (FR-018, SC-004, SC-010)
- [ ] T012 [P] ~~Implementar `src/churn/model_card.py`~~ **Sustituida (D7, I-9)**: el model card se escribe en `src/churn/train.py` (T015); la huella del `.joblib` la añade T129 (FR-004, FR-018, FR-021)
- [ ] T013 [P] Implementar `Cliente` en `src/churn/api.py` con `ConfigDict(extra="forbid")`, `antiguedad_meses` entero "1 ≤ x ≤ 120; sin decimales", `cargo_mensual` número "10 ≤ x ≤ 1.000 (USD)", `reclamos_ult_3m` entero "0 ≤ x ≤ 6; sin decimales", `uso_datos_gb` número "0 ≤ x ≤ 1.000 (GB)", `Literal` tomados de `config.PLANES`, `METODOS_PAGO` y `RENOVACION`, e `id_cliente` opcional "hasta 64 caracteres" (FR-006, FR-007, FR-008)
- [ ] T014 Escribir `tests/integration/test_train.py` (debe fallar): con rutas temporales, el umbral de decisión se calibra en validación y no en prueba; dos corridas dan métricas idénticas; con `data/raw/churn_telco.csv` se cumplen recall ≥ 0,70, precision ≥ 0,40 y ROC-AUC ≥ 0,75; el model card queda escrito sin `rango_edad` en `features`; si una métrica queda bajo el umbral el modelo no queda marcado como promovible; el algoritmo `rf` entrena (FR-016, FR-018, SC-004, SC-010)
- [ ] T015 Implementar `src/churn/train.py` (tras T009–T012 y T014): partición 75/25 estratificada con `config.SEED`, calibración del umbral por validación cruzada estratificada sobre el entrenamiento, evaluación única sobre prueba, guardado de `models/churn_model.joblib` y `models/model_card.json`; opción `--algoritmo rf` solo si la regresión no cumple (FR-016, FR-018, SC-004)
- [ ] T016 Crear `tests/conftest.py` con fixtures: `cliente_valido`, modelo pequeño entrenado en una carpeta temporal, rutas de `config` redirigidas con `monkeypatch` y un `TestClient` creado de forma diferida (importa `churn.api` dentro de la fixture) (FR-016)
- [ ] T017 Ejecutar `python -m churn.train` sobre `data/raw/churn_telco.csv` y revisar `models/model_card.json` frente a los umbrales; si la regresión no cumple, repetir con `--algoritmo rf` (SC-004, SC-010). La aprobación del dueño del modelo es un paso manual posterior (T068)

**Checkpoint**: `uv run pytest tests/unit tests/integration/test_train.py` en verde y existe un model card con métricas.

---

## Phase 3: User Story 1 - Consultar el riesgo de un cliente (Priority: P1) 🎯 MVP

**Goal**: un cliente válido recibe probabilidad, nivel de riesgo, recomendación del catálogo, versión del modelo y aviso de uso responsable.

**Independent Test**: enviar un cliente válido a `POST /predict` y verificar los cinco campos; probabilidad exactamente 0,70 da nivel "alto".

### Tests for User Story 1 ⚠️

- [ ] T018 [P] [US1] Escribir `tests/unit/test_recomendaciones.py`: una entrada por nivel (`alto`, `medio`, `bajo`); ningún texto menciona negar servicio ni cambiar precios (FR-003, FR-017)
- [ ] T019 [P] [US1] Escribir `tests/unit/test_predict.py`: nivel `alto` con probabilidad ≥ 0,70 (0,70 exacto es alto), `medio` "≥ 0,50 y < 0,70", `bajo` "< 0,50"; misma entrada y misma versión dan la misma probabilidad; sin modelo cargado se lanza el error de modelo no disponible (FR-001, FR-002, FR-004, FR-016, SC-001)
- [ ] T020 [P] [US1] Escribir `tests/integration/test_api_predict.py`: respuesta con `probabilidad_churn` entre 0 y 1, `nivel_riesgo`, `recomendacion`, `version_modelo` y `aviso_uso_responsable`; sin modelo responde 503 y no devuelve predicción (FR-001..005, FR-013, SC-001)

### Implementation for User Story 1

- [ ] T021 [P] [US1] Implementar `src/churn/recomendaciones.py`: catálogo fijo con textos provisionales marcados `TODO(retencion)` (el texto definitivo lo define Retención y lo revisa Legal) (FR-003, FR-017)
- [ ] T022 [US1] Implementar `src/churn/predict.py` (tras T021): carga del modelo, probabilidad, nivel de riesgo con los umbrales de `config.py` y selección de la recomendación del catálogo (FR-001, FR-002, FR-003, FR-004)
- [ ] T023 [US1] Añadir `Prediccion` a `src/churn/api.py`: `probabilidad_churn` número 0–1, `nivel_riesgo` (`alto` / `medio` / `bajo`), `recomendacion`, `version_modelo`, `aviso_uso_responsable` (FR-001..005)
- [ ] T024 [US1] Crear `src/churn/api.py` con la aplicación, la carga del modelo al iniciar y `POST /predict`; sin modelo responde 503 sin predicciones inventadas (FR-001..005, FR-013, SC-001)

**Checkpoint**: US1 funciona sola (MVP). `GET /health` y el registro llegan en US6.

---

## Phase 4: User Story 2 - Rechazar datos inválidos con mensajes claros (Priority: P1)

**Goal**: toda solicitud inválida se rechaza con un mensaje que nombra el campo, el motivo y los valores permitidos.

**Independent Test**: enviar a `POST /predict` un valor fuera de rango, un campo faltante, una categoría inválida, un campo extra y `rango_edad`; cada uno devuelve 422 con el campo nombrado.

### Tests for User Story 2 ⚠️

- [ ] T025 [P] [US2] Escribir `tests/integration/test_api_validacion.py`: antigüedad 121 nombra el campo y el rango 1–120; plan inexistente lista los valores permitidos; campo faltante y campo extra nombran el campo; `rango_edad` se rechaza como no previsto y nunca altera la probabilidad; decimales en antigüedad o reclamos se rechazan; el cuerpo de error no repite valores sensibles (FR-006, FR-007, FR-008, SC-002, SC-006)

### Implementation for User Story 2

- [ ] T026 [US2] Añadir en `src/churn/api.py` el manejador de errores de validación: respuesta 422 con `detalle` (lista de `campo`, `mensaje` y valores permitidos cuando aplica), según `contracts/openapi.yaml` (FR-007, SC-002)

**Checkpoint**: US1 y US2 funcionan juntas; el esquema de entrada ya cubre las reglas (T013).

---

## Phase 5: User Story 3 - Puntuar el lote mensual (Priority: P2)

**Goal**: un lote de "1 a 1.000 elementos" devuelve una predicción por cliente en el mismo orden.

**Independent Test**: enviar 1.000 clientes válidos y recibir 1.000 predicciones en orden en menos de 10 s; 1.001, lote vacío y un cliente inválido se rechazan.

### Tests for User Story 3 ⚠️

- [ ] T027 [P] [US3] Escribir `tests/integration/test_api_lote.py`: 1.000 clientes válidos devuelven 1.000 resultados en el mismo orden y en menos de 10 s; 1.001 y lote vacío se rechazan con mensaje del límite; un cliente inválido en la posición 3 rechaza todo el lote e indica la posición y el campo (FR-009, SC-003)
- [ ] T028 [P] [US3] Escribir `tests/unit/test_predict_lote.py`: `predecir_lote` conserva el orden y da la misma probabilidad que la predicción individual del mismo cliente (FR-009, FR-016)

### Implementation for User Story 3

- [ ] T029 [US3] Añadir `Lote` a `src/churn/api.py`: `clientes` "de 1 a 1.000 elementos" usando `config.LOTE_MAX` (FR-009)
- [ ] T030 [US3] Implementar `predecir_lote` vectorizado en `src/churn/predict.py` (FR-009, SC-003)
- [ ] T031 [US3] Añadir `POST /predict/lote` en `src/churn/api.py` y la posición del cliente inválido en el detalle del error (FR-009, SC-003)

**Checkpoint**: US3 funciona sin resumen; el resumen se añade en US4.

---

## Phase 6: User Story 4 - Ver clientes e ingresos en riesgo (Priority: P2)

**Goal**: cada lote puntuado entrega el resumen de clientes e ingresos en riesgo, también guardado como último resumen.

**Independent Test**: puntuar un lote con riesgos conocidos y comparar el resumen con el cálculo manual; un lote sin riesgo alto da ceros.

### Tests for User Story 4 ⚠️

- [ ] T032 [P] [US4] Escribir `tests/unit/test_campana.py` (resumen): total, número y porcentaje en riesgo alto, `ingresos_mensuales_en_riesgo` igual a la suma de `cargo_mensual` de los clientes en riesgo alto, `ingresos_6_meses_en_riesgo` igual a esa suma × 6, ceros si no hay riesgo alto (FR-010, SC-008)
- [ ] T033 [P] [US4] Escribir `tests/integration/test_api_resumen.py`: `POST /predict/lote` incluye `resumen` que coincide con el cálculo manual y se guarda en `reports/metrics/ultimo_lote.json` sin identificadores ni datos por cliente (FR-010, FR-019, SC-008)

### Implementation for User Story 4

- [ ] T034 [US4] Implementar en `src/churn/campana.py` el resumen de riesgo y su guardado en `config.ULTIMO_LOTE_PATH` (solo agregados) (FR-010, SC-008)
- [ ] T035 [P] [US4] Añadir `ResumenRiesgo` a `src/churn/api.py` con los campos de `data-model.md` (FR-010)
- [ ] T036 [US4] Incluir `resumen` en la respuesta de `POST /predict/lote` en `src/churn/api.py` (tras T034 y T035) (FR-010, SC-008)

**Checkpoint**: US4 completa; el último resumen queda disponible para la vista (Fase 10).

---

## Phase 7: User Story 5 - Elegir a quién contactar dentro del presupuesto (Priority: P2)

**Goal**: dado un lote, un presupuesto (2.000 USD por defecto) y un costo (8 USD por defecto), devolver la lista de contacto ordenada por probabilidad.

**Independent Test**: un lote de más de 250 clientes devuelve exactamente 250 contactos y `costo_total` de 2.000 USD.

### Tests for User Story 5 ⚠️

- [ ] T037 [P] [US5] Escribir `tests/unit/test_contactos.py`: `max_contactos` = `floor(presupuesto / costo_por_contacto)`; 2.010 USD da 251; solo se eligen clientes en riesgo alto, ordenados por ingreso esperado (probabilidad × `cargo_mensual`) descendente con desempate estable por posición de entrada; devuelve `min(max_contactos, clientes en riesgo alto)`; lote sin riesgo alto devuelve lista vacía con mensaje; presupuesto menor que el costo devuelve lista vacía con mensaje; presupuesto o costo no positivos se rechazan (FR-011, FR-012, SC-007; D5)
- [ ] T038 [P] [US5] Escribir `tests/integration/test_api_campana.py`: valores por defecto con más de 250 clientes en riesgo alto devuelven 250 contactos y costo de 2.000 USD; con menos clientes en riesgo devuelve solo esos; un lote de 5.000 clientes se acepta y uno de 5.001 se rechaza con 422; `presupuesto` = 0 devuelve 422; la respuesta incluye `aviso_uso_responsable`; cada contacto lleva `posicion_en_lote` y `id_cliente` solo si se envió (FR-005, FR-011, FR-012, SC-007; D5)

### Implementation for User Story 5

- [ ] T039 [US5] Implementar `seleccionar_contactos` en `src/churn/campana.py` (tras T034, mismo archivo) según D5: riesgo alto, orden por ingreso esperado, `min(max_contactos, en riesgo)` (FR-011, FR-012, SC-007)
- [ ] T040 [P] [US5] Añadir `SolicitudContactos` y `ListaContacto` a `src/churn/api.py`: `presupuesto` y `costo_por_contacto` mayores que 0 con valores por defecto 2000 y 8 (FR-011, FR-012)
- [ ] T041 [US5] Añadir `POST /campana/contactos` en `src/churn/api.py` (tras T039 y T040); el tope de clientes por solicitud es `config.CONTACTOS_LOTE_MAX` = 5000 (D5, I-2); `/predict/lote` conserva 1000 (FR-011, FR-012, SC-007)

**Checkpoint**: US5 completa; los contactos nunca superan el presupuesto.

---

## Phase 8: User Story 6 - Saber si el servicio está sano (Priority: P3)

**Goal**: `GET /health` informa el estado y la versión del modelo, y el registro de predicciones guarda solo el identificador codificado.

**Independent Test**: `/health` con y sin modelo; tras varias predicciones con `id_cliente`, el JSONL no contiene ningún identificador en claro.

### Tests for User Story 6 ⚠️

- [ ] T042 [P] [US6] Escribir `tests/unit/test_registro.py`: el hash es SHA-256 de sal + identificador truncado a 16 caracteres hexadecimales; identificador ausente se registra como `null`; sin `CHURN_HASH_SALT` se usa la sal de desarrollo y se emite un aviso (FR-015, SC-005)
- [ ] T043 [P] [US6] Escribir `tests/integration/test_api_salud.py`: con modelo, `estado` = `sano` y la versión; sin modelo, `no_sano` con 503 y las rutas de predicción no devuelven predicciones (FR-013)
- [ ] T044 [P] [US6] Escribir `tests/integration/test_api_registro.py`: tras `/predict` y `/predict/lote` con `id_cliente`, ninguna línea de `logs/predicciones.jsonl` contiene el identificador en claro y cada línea trae marca de tiempo, hash, probabilidad, nivel y versión (FR-015, SC-005)

### Implementation for User Story 6

- [ ] T045 [US6] Implementar `src/churn/registro.py`: hash con sal y escritura de una línea JSONL por predicción en `config.PREDICTIONS_LOG` (FR-015, SC-005)
- [ ] T046 [US6] Añadir `GET /health` en `src/churn/api.py` y su esquema `EstadoServicio` en `src/churn/api.py` (FR-013)
- [ ] T047 [US6] Integrar el registro en `POST /predict` y `POST /predict/lote` de `src/churn/api.py` (tras T045 y T046) (FR-015, SC-005)

**Checkpoint**: US6 completa; la privacidad queda verificada por pruebas.

---

## Phase 9: User Story 7 - Detectar si los datos cambian frente al entrenamiento (Priority: P3)

**Goal**: comparar un lote reciente con la distribución de entrenamiento y clasificar cada variable como estable, alerta o crítico.

**Independent Test**: un lote igual al de entrenamiento da todo estable; una variable desplazada de forma intencional da crítico; un lote de 50 filas da datos insuficientes.

### Tests for User Story 7 ⚠️

- [ ] T048 [P] [US7] Escribir `tests/unit/test_drift.py`: PSI ≈ 0 para un lote igual a la referencia; alerta con PSI ≥ 0,10; crítico con PSI ≥ 0,25; variables categóricas; piso de 1e-4 en proporciones; `estado_general` es el peor de las variables; menos de 100 filas devuelve `datos_insuficientes`; recomienda reentrenar si hay una variable crítica (FR-014, SC-009)
- [ ] T049 [P] [US7] Escribir `tests/integration/test_train_referencia.py`: tras entrenar, el model card trae `perfil_referencia` con las 7 variables, los límites internos de los deciles (hasta 9; menos si hay repetidos) en las numéricas y la proporción por categoría en las categóricas, calculados solo con el split de entrenamiento (FR-014, SC-009; D6)
- [ ] T050 [P] [US7] Escribir `tests/integration/test_api_drift.py`: `POST /drift` con datos de entrenamiento da `estable`; con `cargo_mensual` desplazado da `critico`; con 50 clientes da `datos_insuficientes`; el informe se guarda en `reports/metrics/drift.json` (FR-014, SC-009)

### Implementation for User Story 7

- [ ] T051 [US7] Implementar `src/churn/drift.py`: construir la referencia, PSI por variable (Σ (p_nuevo − p_ref) · ln(p_nuevo / p_ref)) y clasificación con `PSI_ALERTA` y `PSI_CRITICO`, `MIN_FILAS_DRIFT` para lotes pequeños (FR-014, SC-009)
- [ ] T052 [US7] `src/churn/train.py` guarda `perfil_referencia` en el model card (ya lo hace; falta la prueba T049) (FR-014)
- [ ] T053 [P] [US7] Añadir `InformeCambioDatos` a `src/churn/api.py` con los campos de `data-model.md` (FR-014)
- [ ] T054 [US7] Añadir `POST /drift` en `src/churn/api.py` y el guardado del informe en `config.DRIFT_REPORT_PATH` (tras T051 y T053) (FR-014, SC-009)
- [ ] T055 [US7] Añadir a `src/churn/drift.py` el punto de entrada `python -m churn.drift --escenario <nombre>` que usan `tareas.py` y el `Makefile`, leyendo lotes de `data/drift/` (FR-014)

**Checkpoint**: US7 completa; las siete historias funcionan por separado.

---

## Phase 10: Vista visual de solo lectura (FR-019, transversal)

**Goal**: `/dashboard` muestra estado, último resumen de riesgo y último informe de cambio de datos, sin acciones ni identificadores. Depende de US4, US6 y US7.

**Independent Test**: abrir `/dashboard` antes de puntuar (mensaje claro de que no hay datos) y después (cifras visibles, sin identificadores).

### Tests ⚠️

- [ ] T056 [P] Escribir `tests/integration/test_api_vista.py`: `GET /metrics` sin lote devuelve `ultimo_resumen` y `ultimo_cambio_datos` nulos; con lote devuelve ambos; ninguna respuesta contiene identificadores; `GET /dashboard` responde HTML (FR-019)
- [ ] T057 [P] Escribir `tests/unit/test_dashboard_html.py`: `dashboard/index.html` no carga scripts ni estilos externos (sin CDN), no contiene formularios ni peticiones que envíen datos, e inserta el texto recibido escapado (FR-019, FR-017)

### Implementation

- [ ] T058 Añadir `GET /metrics` en `src/churn/api.py`: modelo del model card, último resumen y último informe de cambio de datos, sin identificadores (FR-010, FR-014, FR-019)
- [ ] T059 Añadir `GET /dashboard` en `src/churn/api.py` sirviendo `dashboard/index.html` (tras T058) (FR-019)
- [ ] T060 [P] Ajustar `dashboard/index.html` (ya existe): consulta solo `/health` y `/metrics`, JavaScript y CSS en línea, mensaje claro cuando no hay datos, sin acciones (FR-019)

**Checkpoint**: la vista funciona con y sin datos.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [ ] T061 [P] Crear `Dockerfile` opcional (imagen base de Python 3.11, instalar el paquete y ejecutar `uvicorn churn.api:app`); sin registro con cuenta (plan: Docker opcional)
- [ ] T062 [P] Actualizar `scripts/smoke_test.py` para cubrir `/health` (contrato `estado == "sano"`, D8), `/predict`, `/predict/lote`, `/campana/contactos`, `/drift` y `/dashboard`; la corrección del contrato actual es T112 (SC-001, SC-007, SC-009)
- [ ] T063 [P] Actualizar `README.md` con la guía de uso de las nuevas rutas, indicando que los datos son sintéticos y que el texto del catálogo es provisional (FR-005; ASUM-DM §9)
- [ ] T064 Reemplazar en `src/churn/recomendaciones.py` los textos provisionales por los que entregue Retención y revise Legal; **bloqueada hasta recibirlos** (FR-003)
- [ ] T065 **Resuelta por decisión (D5)**: ya no espera al dueño. D-09 se implementa en T039–T041 y D-10 en T117 (k = 5 % del conjunto evaluado) (FR-011, SC-004, SC-007)
- [ ] T066 (después de la Fase 12) Ejecutar `uv run pytest` completo y los 18 escenarios de `quickstart.md`; corregir lo que falle (SC-001 a SC-010)
- [x] T067 Actualizar las referencias a `specs/001-api-churn` en `AGENTS.md`: hecho el 2026-11-06 tras confirmar el dueño del proyecto que la 002 sustituye a la 001; la 001 quedó marcada como reemplazada (constitución: precedencia de las fuentes)
- [ ] T068 Registrar la aprobación del dueño del modelo en `models/model_card.json` (`aprobado_por`, `fecha`); **paso manual**, sin él no hay salida a producción (constitución VI)

---

## Phase 12: Seguridad, privacidad y equidad (FR-020 a FR-025 y precisiones del checklist)

**Purpose**: requisitos añadidos tras revisar `checklists/seguridad-privacidad-equidad.md`. Las pruebas van primero y deben fallar. Los IDs continúan a partir de T069 para no renumerar las fases anteriores; esta fase se ejecuta antes de T066.

### Tests ⚠️

- [ ] T069 [P] Escribir `tests/unit/test_limitador.py`: la solicitud 61 de una misma IP en un minuto se rechaza con 429 y el mismo formato de error de la API (`{"error": …}`); otra IP no se ve afectada; el contador se reinicia al pasar el minuto (FR-020)
- [ ] T070 [P] Escribir `tests/unit/test_integridad_modelo.py`: un modelo cuya huella (SHA-256 del `.joblib`, guardada en `models/model_card.json`, I-8) no coincide no se sirve; con el archivo alterado `/predict` responde 503 y `/health` informa `no_sano` (FR-021, FR-013)
- [ ] T071 [P] Escribir `tests/integration/test_api_errores.py`: ningún error contiene trazas, rutas de archivos ni el valor recibido de `id_cliente`; presupuesto fuera de 0,01–100.000 y costo fuera de 0,01–1.000 se rechazan con mensaje claro (campo, motivo y valores permitidos) (FR-007, FR-012, FR-022)
- [ ] T072 [P] Escribir `tests/unit/test_registro_campos.py`: cada línea del registro contiene solo `fecha`, `id_codificado`, `probabilidad_churn`, `nivel_riesgo` y `version_modelo`; las líneas de más de 90 días se eliminan (FR-023)
- [ ] T073 [P] Escribir `tests/unit/test_equidad.py`: el model card trae `revision_proxies` con la diferencia de recall por grupo al quitar `metodo_pago`, `tipo_plan` y `antiguedad_meses`; el reparto del 5 % de mayor riesgo se compara con el peso de cada grupo; un modelo con diferencia de recall > 0,05, ratio de impacto dispar < 0,80 o un grupo con menos de 100 clientes no queda aprobado (FR-018, FR-024, SC-010)
- [ ] T074 [P] Escribir `tests/unit/test_resumen_minimo.py`: un lote de menos de 20 clientes no publica resumen y devuelve "lote demasiado pequeño para resumir" (FR-010)
- [ ] T075 [P] Escribir `tests/unit/test_id_cliente.py`: `id_cliente` acepta hasta 64 caracteres entre letras, números, guion y guion bajo; rechaza 65 caracteres y cualquier otro símbolo (FR-006, FR-007)
- [ ] T076 [P] Escribir `tests/unit/test_recomendaciones_terminos.py`: ninguna entrada del catálogo contiene negar, suspender, cancelar el servicio, subir el precio, aumentar la tarifa ni cobrar más (FR-003, FR-017)

### Implementation

- [ ] T077 [P] Implementar `src/churn/limitador.py`: límite por IP en memoria, solo con la librería estándar, configurable en `config.LIMITE_SOLICITUDES_POR_MINUTO` (60 por defecto) (FR-020)
- [ ] T078 Integrar el limitador en `src/churn/api.py` (tras T077) y responder 429 con mensaje claro (FR-020)
- [ ] T079 [P] Implementar en `src/churn/predict.py` la comprobación de la huella del modelo al cargarlo, contra `models/model_card.json` (FR-021)
- [ ] T080 Ajustar `src/churn/api.py` (tras T078): errores sin trazas ni valor del identificador; `presupuesto` de 0,01 a 100.000 y `costo_por_contacto` de 0,01 a 1.000 (FR-007, FR-012, FR-022)
- [ ] T081 [P] Ajustar `src/churn/registro.py`: solo los cinco campos y retención de 90 días (`config.RETENCION_REGISTRO_DIAS`) (FR-023)
- [ ] T082 [P] Ampliar `src/churn/evaluate.py`: reparto del 5 % de mayor riesgo por grupo de edad, tamaño de cada grupo y regla de no aprobación (diferencia de recall > 0,05, ratio de impacto dispar < 0,80 o grupo con menos de 100 clientes) (FR-018, SC-010)
- [ ] T083 Ampliar `src/churn/train.py` (tras T082): comparar el modelo con y sin `metodo_pago`, `tipo_plan` y `antiguedad_meses` y guardar `revision_proxies` en el model card (FR-024)
- [ ] T084 [P] Ajustar `src/churn/campana.py`: el resumen exige al menos 20 clientes (FR-010)
- [ ] T085 Ajustar `src/churn/api.py` (tras T080): patrón y longitud de `id_cliente` (FR-006)
- [ ] T086 [P] Añadir a `src/churn/recomendaciones.py` la lista de términos prohibidos (ampliable por Legal) y su validación al cargar el catálogo (FR-003, FR-017)
- [ ] T087 [P] Escribir `docs/AUDITORIA_EQUIDAD.md`: procedimiento trimestral para cruzar predicciones con el grupo de edad del sistema de origen y reportar diferencias, y definición de la revisión humana (aprobación de la lista por un analista, con nombre y fecha en el proceso de campaña) (FR-005, FR-025)
- [ ] T088 [P] Documentar en `README.md` el secreto del codificado (`CHURN_HASH_SALT`), la retención del registro, el acceso solo local del taller y lo necesario antes de producción (autenticación, control de acceso, derechos sobre los datos) (FR-015, FR-023)

**Checkpoint**: `uv run pytest` en verde con las pruebas de seguridad, privacidad y equidad; el checklist `seguridad-privacidad-equidad.md` listo para revisión.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sin dependencias.
- **Foundational (Fase 2)**: depende de Setup; bloquea todas las historias.
- **US1 (Fase 3)** y **US2 (Fase 4)**: dependen de la Fase 2. US2 solo añade el manejador de errores sobre `api.py`, así que sigue a T024.
- **US3 (Fase 5)**: depende de US1 (reutiliza `predict.py` y `api.py`).
- **US4 (Fase 6)**: depende de US3 (extiende `POST /predict/lote`).
- **US5 (Fase 7)**: depende de US3 y de T034 (comparte `campana.py`).
- **US6 (Fase 8)**: depende de US1 (el registro se integra en las rutas existentes).
- **US7 (Fase 9)**: depende de la Fase 2 (`train.py`) y de US3 para el esquema `Lote`.
- **Fase 10 (vista)**: depende de US4, US6 y US7.
- **Fase 12 (seguridad, privacidad y equidad)**: depende de las historias que toca (US1–US6) y de la Fase 2; se completa antes de T066.
- **Polish (Fase 11)**: depende de las historias deseadas; T064 y T068 dependen de decisiones externas (T065 y T067 ya están resueltas).
- **Fase 14 (corrección tras la auditoría)**: fija el orden de ejecución de lo pendiente por etapas; en caso de diferencia con las fases 3–13, manda la Fase 14.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- Esquemas y módulos de lógica antes que las rutas de `api.py`.
- Las tareas que tocan el mismo archivo (`api.py`, `campana.py`, `predict.py`, `train.py`) van en secuencia, sin `[P]` entre ellas.

### Parallel Opportunities

- Fase 1: T002 en paralelo con T001.
- Fase 2: las pruebas T004–T008 en paralelo; luego T009–T013 en paralelo (archivos distintos).
- Cada historia: todas sus pruebas `[P]` juntas; `recomendaciones.py` (T021), `ResumenRiesgo` (T035) y `SolicitudContactos` (T040) en paralelo con la lógica de otro archivo.
- Tras US1 y US3: US4, US5, US6 y US7 pueden avanzar en paralelo entre personas distintas, coordinando los cambios a `api.py`.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 juntas (deben fallar):
Task: "Escribir tests/unit/test_recomendaciones.py"
Task: "Escribir tests/unit/test_predict.py"
Task: "Escribir tests/integration/test_api_predict.py"

# Luego, en paralelo con otro archivo:
Task: "Implementar src/churn/recomendaciones.py"
```

## Parallel Example: Fase 2

```bash
Task: "tests/unit/test_dataset.py"   Task: "tests/unit/test_features.py"
Task: "tests/unit/test_evaluate.py"  Task: "tests/unit/test_cliente.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Fase 1 y Fase 2 completas, incluido `python -m churn.train` (T017).
2. Fase 3 (US1) y Fase 4 (US2).
3. **Parar y validar**: `POST /predict` con datos válidos e inválidos (escenarios 2–5 de `quickstart.md`).

### Incremental Delivery

1. MVP → US3 (lote) → US4 (resumen) → US5 (contactos): la campaña mensual queda utilizable.
2. US6 (salud y privacidad) y US7 (cambio de datos): operación y monitoreo.
3. Fase 10 (vista) y Fase 11 (cierre y pendientes externos).

---

## Notes

- 135 tareas (T001–T135). `[P]` solo donde no hay conflicto de archivos. Los IDs T069–T088 (Fase 12) se ejecutan antes de T066; las etapas de la Fase 14 ordenan lo pendiente.
- Cada tarea cita el FR o SC que cubre; la matriz FR → prueba de `plan.md` sigue siendo la referencia.
- Antes de cerrar cada tarea: `uv run pytest` en verde (constitución II).
- Pendientes que no son de código: T064 (textos de Retención y Legal) y T068 (aprobación del dueño del modelo).

---

## Phase 13: Convergence

- [ ] T089 Aplicar D2: el servicio sigue sirviendo un modelo no aprobado; `/health` informa `aprobado_para_despliegue` y `alertas`, y cada respuesta de `/predict` y `/predict/lote` lleva `alerta_equidad`. Pruebas T124, implementación T125 (SC-010, FR-018, FR-026, FR-028)
- [ ] T090 Alinear el model card con `data-model.md` conservando los nombres del código (I-10) y añadir lo que falta: `hash_modelo` (T129), `revision_proxies`, `razones_no_aprobado`, precision en el 5 %, precision por grupo y reparto del 5 % (T120–T121). `data-model.md` ya está enmendado (FR-018, FR-021, FR-024)
- [ ] T091 Centralizar los límites de entrada en `src/churn/config.py` (`CARGO_MIN`, `CARGO_MAX`, `USO_DATOS_MAX`, `LOTE_MAX`, `MIN_FILAS_DRIFT`, `TOP_EVALUACION`, rangos de antigüedad y reclamos) y usarlos desde `src/churn/api.py`, `src/churn/dataset.py` y `src/churn/features.py`; no duplicar las constantes que T003 ya preveía (`UMBRAL_RIESGO_MEDIO`, `AVISO_USO_RESPONSABLE`, `MAX_DIF_RECALL` ya existen) per plan: límites en `config.py`, FR-006 (partial)
- [ ] T092 Mejorar los mensajes de validación en `src/churn/api.py`: el rango fuera de límites debe nombrar el rango completo (p. ej. "entre 1 y 120") y la lista de categorías debe usar "o" en español; añadir las comprobaciones en `tests/integration/test_api_validacion.py` per FR-007 (partial)
- [ ] T093 ~~Unificar nombres con el plan~~ **Obsoleta (D7)**: se conservan `predict.py` y `Cliente`/`Prediccion` en `api.py`; plan y tareas ya están actualizados
- [ ] T094 Actualizar `contracts/openapi.yaml` y `data-model.md` para que el cuerpo del 422 incluya `error` ("Entrada inválida") además de `detalle`, y el 500 y el 503 devuelvan `{"error": ...}` per plan: contratos (partial)
- [ ] T095 **Sustituida (D1)**: la compuerta de promoción incluye precision en el 5 % y ROI ≥ 3 en T116–T121 (SC-004, FR-018)
- [ ] T096 Decidido (D6): se conserva el CSV como fuente de verdad. Añadir en `tests/unit/test_dataset.py` una prueba que valide `data/raw/churn_telco.csv` con `validar_calidad` (la columna `periodo` se tolera y no entra al modelo) y documentar en el docstring de `generar()` y en el README que el generador es solo para demos y pruebas (FR-016)
- [ ] T097 Escribir en `tests/unit/test_features.py` una prueba a nivel de modelo: dos conjuntos idénticos salvo `rango_edad` dan la misma `predict_proba` per FR-008 / SC-006 (partial)
- [ ] T098 Escribir en `tests/integration/test_api_predict.py` una prueba de que `POST /predict` responde en menos de 1 s con el modelo de prueba per SC-003 (partial)
- [ ] T099 Escribir `tests/integration/test_api_rutas.py`: la aplicación solo expone rutas de consulta y puntuación, ninguna crea, modifica o borra datos del cliente per FR-017 (partial)
- [ ] T100 Decidido (D3): se conserva `ratio_impacto_dispar` en `src/churn/evaluate.py`; lo respalda SC-010 (≥ 0,80) y se prueba en `tests/unit/test_evaluate.py` (T116) (SC-010)
- [ ] T101 Reconciliar las casillas de esta lista con el código: revisar T005, T006, T008, T010, T011, T016, T018, T019, T020–T026 y marcar solo las que cumplan su descripción completa, anotando lo que falte per Constitution I (partial)
- [ ] T102 Decidir si `models/churn_model.joblib`, `models/model_card.json` y `reports/metrics/evaluacion.json` se versionan o van a `.gitignore`, y documentarlo en `README.md` per Constitution VI (unrequested)

---

## Phase 14: Corrección tras la auditoría (`docs/AUDITORIA.md`, decisiones en `docs/DECISIONES.md`)

**Reglas**: spec/plan/tareas ya actualizados (Etapa 0). En cada etapa las pruebas van antes y deben fallar; nunca se relajan criterios; `rango_edad` solo audita. Cada etapa termina con `uv run pytest -q` en verde, los comandos de la Fase 2 que apliquen, `docs/AUDITORIA.md` actualizado y un commit "etapa N: …". Las tareas antiguas que aparecen en el orden de ejecución se hacen con el texto ya enmendado arriba.

### Etapa 1 · Bloqueantes: funcionar de punta a punta (B1, B3, B4)

- [ ] T103 [P] Ampliar `tests/unit/test_config.py`: existen `MIN_PRECISION_TOP` = 0.40, `MIN_ROI` = 3, `MIN_RATIO_IMPACTO` = 0.80, `TOP_EVALUACION` = 0.05, `CONTACTOS_LOTE_MAX` = 5000, `LOTE_MAX` = 1000, `LIMITE_SOLICITUDES_POR_MINUTO` = 60 (FR-009, FR-011, FR-018, FR-020, SC-010; D1, D3, D5)
- [ ] T104 Añadir esas constantes a `src/churn/config.py` (tras T103) sin tocar las existentes (FR-009, FR-011, FR-018, FR-020)
- [ ] T105 [P] Escribir `tests/unit/test_dataset_crisis.py`: `aplicar_crisis(df)` sube `cargo_mensual` un 30 % (tope 1.000) y duplica `reclamos_ult_3m` (tope 6) sin modificar las demás columnas ni el original; es determinista (FR-014, FR-016; D6)
- [ ] T106 Implementar `aplicar_crisis` en `src/churn/dataset.py` (tras T105) y documentar en el docstring de `generar()` que es solo para demos y pruebas (FR-014, FR-016; D6)
- [ ] T107 [P] Escribir `tests/unit/test_drift_escenarios.py`: el escenario base (split de prueba del CSV) da PSI < 0,10 en las 7 variables y `estado_general` = `estable`; el escenario crisis da `critico` y solo cambian las variables afectadas por la transformación; `simular` no usa `generar` (FR-014, SC-009; D6)
- [ ] T108 Ajustar `src/churn/drift.py` (`simular` y `main`) para que la referencia sea el `perfil_referencia` del split de entrenamiento, el base sea el split de prueba y la crisis sea `aplicar_crisis` sobre ese mismo split (tras T106 y T107) (FR-014, SC-009; D6)
- [ ] T109 [P] [US7] Escribir `tests/integration/test_api_drift_get.py`: `GET /drift` devuelve el último informe de `reports/metrics/drift.json`; sin informe responde 404 con `{"error": …}` claro (FR-014)
- [ ] T110 [US7] Añadir `GET /drift` en `src/churn/api.py` (tras T109, T054) (FR-014)
- [ ] T111 [P] Escribir `tests/integration/test_smoke_contrato.py`: `scripts/smoke_test.py` expone `verificar_api(cliente)` que pasa con el contrato `/health` = `{"estado": "sano", …}` y falla con `{"status": "ok"}` (D8)
- [ ] T112 Corregir `scripts/smoke_test.py` (tras T111): usar `estado == "sano"`, extraer `verificar_api`, y llamar `entrenar(cargar_datos(...))` con sus argumentos si falta el modelo (D8; hallazgo B4)
- [ ] T113 [P] Escribir `tests/unit/test_simular_trafico.py`: con `urlopen` simulado, un `HTTPError` 404 se informa como error HTTP (no como «no se pudo conectar»); la crisis sale de `aplicar_crisis` sobre el CSV (FR-014; D6)
- [ ] T114 Corregir `scripts/simular_trafico.py` (tras T113, T106): distinguir `HTTPError` de `URLError` y usar `aplicar_crisis` (hallazgo M5; D6)
- [ ] T115 Cerrar la Etapa 1: `uv run pytest -q`; `python -m churn.drift --escenario base` (sin alerta crítica), `--escenario crisis` y `python scripts/simular_trafico.py --escenario crisis` con la API arriba; actualizar `docs/AUDITORIA.md`; commit
- **Orden de ejecución de la etapa**: T103 → T104 → T105 → T106 → T107 → T108 → T027–T031 (lote) → T032–T036, T074, T084 (resumen) → T037–T041 (contactos) → T048, T050, T053, T054 (POST /drift) → T109 → T110 → T056–T060 (vista) → T111 → T112 → T113 → T114 → T115.

### Etapa 2 · Gobernanza y equidad (B5, I1–I4, I6; D1–D4)

- [ ] T116 [P] Ampliar `tests/unit/test_evaluate.py`: precision en el `TOP_EVALUACION` (5 %) contra un valor calculado a mano; ROI estimado con la fórmula de FR-018; ratio de impacto dispar y su regla ≥ 0,80; precision por grupo (FR-018, SC-004, SC-010; D1, D3)
- [ ] T117 Implementar en `src/churn/evaluate.py` (tras T116) `precision_en_top`, `roi_estimado` y la precision por grupo; conservar `ratio_impacto_dispar` (FR-018, SC-004, SC-010)
- [ ] T118 [P] Escribir `tests/integration/test_train_umbral.py`: (a) con umbral viable elige el de mayor precision con recall ≥ `MIN_RECALL`; (b) sin umbral viable elige el de mayor recall, no lanza excepción, guarda el modelo con `criterios_cumplidos` detallado y `aprobado_para_despliegue=False`; ambos caminos (FR-027; D4)
- [ ] T119 Ajustar `calibrar_umbral` en `src/churn/train.py` (tras T118): quitar el `RuntimeError` y aplicar la regla de FR-027 (FR-027; D4)
- [ ] T120 [P] Ampliar `tests/integration/test_train.py`: el card trae los 5 criterios, `equidad_recall`, `ratio_impacto_dispar`, `tamano_grupos`, `razones_no_aprobado` (vacía solo si todo cumple), `revision_proxies` y `metricas_test` con precision en el 5 %; `aprobado_para_despliegue` es verdadero solo si todo se cumple (FR-018, FR-024, SC-004, SC-010; D1, D3)
- [ ] T121 Ampliar `src/churn/train.py` (tras T117, T119, T120; incluye T082 y T083): criterios de D1 y D3, `razones_no_aprobado`, `revision_proxies` con y sin `metodo_pago`, `tipo_plan` y `antiguedad_meses` (FR-018, FR-024, SC-010)
- [ ] T122 [P] Escribir `tests/unit/test_mitigacion.py`: compara regresión logística y Random Forest, y el modelo sin cada variable que sustituya a la edad; devuelve brecha de recall y ratio por variante; nunca usa `rango_edad` como variable ni fija umbrales por grupo; es determinista con `config.SEED` (FR-024, SC-010; D2)
- [ ] T123 Implementar `src/churn/mitigacion.py` (`python -m churn.mitigacion`) que escribe `reports/metrics/mitigacion_equidad.json` (tras T121, T122); ejecutarlo y reportar los números; si ninguna variante baja de 0,05, documentarlo sin forzar (FR-024; D2)
- [ ] T124 [P] Escribir pruebas en `tests/integration/test_api_predict.py` y `test_api_salud.py`: con el model card no aprobado, `/predict` y cada elemento de `/predict/lote` traen `alerta_equidad` con la razón además del aviso; `/health` trae `aprobado_para_despliegue=false` y `alertas`, con `estado` = `sano`; con el card aprobado no hay alerta ni `alertas` (FR-026, FR-028; D2, D8)
- [ ] T125 Implementar en `src/churn/api.py` (tras T121, T124) `alerta_equidad` en `Prediccion` y `alertas` en `EstadoServicio` (FR-026, FR-028)
- [ ] T126 Documentar en `docs/GOBERNANZA.md` la promoción manual, la alerta de equidad y la regla de FR-027 (D2, D4; constitución VI)
- [ ] T127 Cerrar la Etapa 2: `uv run pytest -q`, `python -m churn.train`, `python -m churn.mitigacion`; actualizar `docs/AUDITORIA.md` (B5, I1–I4, I6); commit
- **Orden de ejecución de la etapa**: T116 → T117 → T118 → T119 → T120 → T121 → T122 → T123 → T124 → T125 → T126 → T127 (T073 y T082–T083 se absorben en T116–T121).

### Etapa 3 · Privacidad y seguridad (B2, I5)

- [ ] T128 [P] Ampliar `tests/integration/test_train.py`: `models/model_card.json` trae `hash_modelo` igual al SHA-256 del `.joblib` (FR-021; I-8)
- [ ] T129 Guardar `hash_modelo` en `models/model_card.json` al entrenar (`train.py`) y verificarlo en `predict.cargar_modelo` contra el archivo (tras T128, T070): si no coincide, `ModeloNoDisponible` (FR-021)
- [ ] T130 Cerrar la Etapa 3 tras ejecutar, en este orden: T042 → T043 → T044 (pruebas de registro y salud) → T045 → T047 (registro cableado, `latencia_ms` fuera de la línea y retención, T072 y T081) → T069 → T077 → T078 (429 con formato de error) → T070 → T079 (integridad) → T071 → T080 (422/500 sin valores ni trazas). Verificar con `uv run pytest -q`, que `logs/predicciones.jsonl` exista y no contenga ningún `id_cliente` en claro, 61 solicitudes → 429 y un `.joblib` alterado → 503 y `no_sano`; actualizar `docs/AUDITORIA.md` (B2, I5); commit

### Etapa 4 · Menores, documentación y cierre

- [ ] T131 Actualizar `README.md` (T063, T088): conteo real de pruebas, comandos que funcionan en macOS con su salida real, estado real de las rutas, variantes `/speckit-*` (Claude Code) y `/speckit.*` (OpenCode) (D9), nota de que el generador es solo para demos (D6), quitar la referencia a `referencia/`
- [ ] T132 Añadir a `business/ASUM-DM.md` la sección de brecha de la meta de −3 pp (cuánto mueve la tasa la campaña actual y cuántos contactos y presupuesto harían falta), como riesgo abierto del negocio (D10)
- [ ] T133 Resolver los hallazgos 🟡 restantes de `docs/AUDITORIA.md` (M3, M4, M6–M12): `dependency-groups` o aviso de `uv sync`, `Makefile`/`tareas.py` con `uv run`, mensajes de validación (T091, T092, T094), campo `campo` en JSON malformado, skills y `PLAN_B` que aún apuntan a la 001, `.gitignore` (T102), `Dockerfile` (T061)
- [ ] T134 Reconciliar las casillas de este archivo con el código y las pruebas (T101)
- [ ] T135 Repetir la auditoría completa (5 fases) y agregar a `docs/AUDITORIA.md` la sección «Re-auditoría» con la tabla antes/después por severidad; justificar todo lo que siga abierto; commit
