# Auditoría técnica · Churn Telco (taller ASUM-DM + SDD + MLOps)

Fecha: 2026-11-06 · Rama `main` (sin commits nuevos; casi todo el código está sin versionar) · Alcance: repositorio completo.
Regla seguida: no se modificó código, specs ni configuración; solo se creó este informe.
**Actualizado el 2026-11-07:** el seguimiento por etapas está en la sección 7 y la re-auditoría completa, con la tabla antes/después, en la sección 8.

**Fuente de verdad real.** El pedido citaba `specs/001-api-churn/` (spec, plan, tareas). Esa carpeta solo tiene `spec.md` y
`checklists/requirements.md`, y está marcada «Reemplazada por 002» (`specs/001-api-churn/spec.md:7`). La auditoría se hizo contra
`specs/002-campana-retencion-monitoreo/` (spec, plan, research, data-model, contracts, tasks, checklists). Tampoco existe
`docs/prompts_taller.md`: el archivo equivalente es `prompts/PROMPTS_OPENCODE.md`.

**Artefactos generados por los comandos de la auditoría** (se dicen aquí porque la regla pedía declararlos):
- `uv run python -m churn.train` sobrescribió `models/churn_model.joblib` y `models/model_card.json`. Todas las claves del card quedaron
  idénticas salvo `fecha_entrenamiento` (2026-11-07T00:49:09 → 01:09:42), lo que además prueba la reproducibilidad. El `.joblib` cambia byte a byte
  porque lleva la fecha. `reports/metrics/evaluacion.json` quedó idéntico.
- `python -m churn.drift --escenario crisis` sobrescribió `reports/metrics/drift.json`.
- `uv sync` / `uv sync --extra dev` modificaron `.venv/`; `pytest` creó `__pycache__/` y `.pytest_cache/`.
- `data/raw/churn_telco.csv` no cambió (md5 `81bced38…` antes y después). `logs/` quedó vacío.
- Copia previa de `models/`, `reports/`, `data/raw/` y `logs/`: `/private/tmp/claude-501/-Users-laasanchezgi-Code-learning-udea-machine-learning-1-taller-churn-mlops/22547db4-cc9c-4e23-9ba6-5ceaa1b45d9d/scratchpad/antes/`.
- Se levantó `uvicorn` en el puerto 8000 durante unos minutos y se detuvo.

---

## 1. Resumen ejecutivo

1. **No funciona de punta a punta.** Solo existen `POST /predict`, `GET /health` y `GET /metrics`; `/predict/lote`, `/campana/contactos`, `/drift` y `/dashboard` responden 404, así que `scripts/simular_trafico.py` falla y no hay campaña, resumen de riesgo ni dashboard.
2. El núcleo de ML sí funciona y es reproducible: 5.000 filas, `pytest` 106 de 106 en verde, ROC-AUC 0,811, recall 0,734, precision 0,493 (cumple los tres criterios del spec).
3. **No cumple la equidad (SC-010):** brecha de recall entre grupos de edad de 0,147 frente al máximo de 0,05. El modelo queda con `aprobado_para_despliegue=False`, pero el servicio lo sirve igual y `/health` dice «sano».
4. La privacidad solo está demostrada en `registro.py` (unitaria): la API **no escribe el JSONL**, por lo que FR-015/FR-023/SC-005 no se cumplen en el servicio. Faltan además el límite de solicitudes (FR-020) y la comprobación de integridad del modelo (FR-021).
5. Hay contradicciones entre artefactos que necesitan su decisión (criterios de promoción de 5 vs 3, CSV que no sale del generador, IDs y orden de los prompts, nombres del plan frente al código). Se plantean en la sección 6.

**Hallazgos: 5 bloqueantes · 11 importantes · 12 menores.**

---

## 2. Resultado de la Fase 2 (ejecución real)

| # | Comando | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| 1 | `uv sync` | Entorno listo | Sale con 0, pero **desinstala** `pytest`, `httpx` y los demás extras `dev` (`- pytest==9.2.0`). Después `uv run pytest` falla: `error: Failed to spawn: pytest … No such file or directory`. Con `uv sync --extra dev` (lo que documentan README y AGENTS.md) todo se instala. | ⚠️ |
| 2 | `uv run python -m churn.dataset` | 5000 filas, churn ≈ 25 % | Imprime `5000 filas · escenario base · churn 24.7%` y `ya existe; use --forzar`. **No escribe nada.** El CSV en disco tiene 5.000 filas, churn **25,5 %** y una columna extra `periodo`: no sale del generador. | ⚠️ |
| 3 | `uv run python -m churn.train` | ROC-AUC ≥ 0,75, recall ≥ 0,70, precision ≥ 0,40 | `logreg · umbral 0.538 · recall 0.734 · precision 0.493 · ROC-AUC 0.811`. Criterios técnicos ✅; `equidad_recall: False` → `aprobado_para_despliegue = False`. | ✅ (técnico) / ❌ (equidad) |
| 4 | `uv run pytest -q` | Todo en verde | `106 passed in 0.99s` (con extras `dev`). README dice 80. | ✅ |
| 5 | `uv run python -m churn.drift --escenario crisis` | Informe PSI + comparación | Funciona. Crisis: `cargo_mensual` PSI 0,532 y `uso_datos_gb` 0,258 en crítico; `antiguedad_meses` y `reclamos_ult_3m` en alerta. **Pero** el «base» comparado ya sale crítico (`uso_datos_gb` 0,270, `cargo_mensual` 0,167) y con recall 0,602 / ROC-AUC 0,728; en «crisis» el recall *sube* a 0,735 y `alerta_recall=False`. | ⚠️ |
| 6 | `uv run python scripts/simular_trafico.py --escenario crisis` | Envía clientes a la API | Sin API: `Connection refused`. Con API arriba: `No se pudo conectar a http://localhost:8000: HTTP Error 404: Not Found` (`/predict/lote` no existe; el mensaje engaña). | ❌ |
| 7 | Importar `churn.api:app`; `/predict`, `/health`, `/metrics` | Existen | `openapi.json` lista solo `/predict`, `/health`, `/metrics`. Los tres responden bien. `/dashboard`, `/predict/lote`, `/campana/contactos`, `/drift` → 404. | ✅ (3 pedidas) / ❌ (spec) |
| + | `uv run python scripts/smoke_test.py --sin-ia` (comando de AGENTS.md) | `Todo listo para el taller.` | `[FALLA] API /health modelo v1.0.0` → «1 verificación(es) obligatoria(s) fallaron». | ❌ |
| + | `make datos` (macOS) | Genera datos | `make: python: No such file or directory` (solo hay `python3`). | ❌ |

Comprobaciones adicionales hechas contra la API real: dato válido → 200 con los 5 campos; `rango_edad` → 422 «campo no previsto»; `antiguedad_meses=121` → 422; `tipo_plan` inválido → 422; `id_cliente` con símbolos o de 65 caracteres → 422 sin repetir el valor; 71 solicitudes seguidas → todas 200 (no hay límite); sin modelo → `/health` 503 `no_sano` y `/predict` 503 (con `TestClient` y `config.MODEL_PATH` apuntando a un archivo inexistente).

---

## 3. Matriz de trazabilidad

KPI = KPI de `business/ASUM-DM.md` §1.2. Principio = constitución I–VII. ✅ cumple · ⚠️ parcial · ❌ falta.

| KPI | Principio | Req. | Tarea | Archivo | Prueba | Estado |
|---|---|---|---|---|---|---|
| Tasa de cancelación | I, VII | FR-001 | T022, T024 | `predict.py`, `api.py:115` | `tests/integration/test_api_predict.py`, `tests/test_api.py` | ✅ |
| Tasa de cancelación | I | FR-002 | T019, T022 | `predict.py:26` | `test_api_predict.py` (0,70 → alto; 0,699 → medio) | ✅ |
| Tasa de cancelación | VII | FR-003 | T021, T086, T064 | `recomendaciones.py` (textos `TODO(retencion)`) | ninguna (faltan `test_recomendaciones*.py`) | ⚠️ |
| Gobernanza | VI | FR-004 | T022 | `predict.py:46` | `test_api_predict.py` | ✅ |
| Uso responsable | VII | FR-005 | T024, T038 | `api.py:123`, `config.py:73` | `test_api.py:22` (solo `/predict`) | ⚠️ (sin lista de contacto) |
| Calidad de datos | IV | FR-006 | T008, T013 | `api.py:25-33` | `test_api_validacion.py` | ✅ (límites duplicados en `api.py`/`dataset.py`, T091) |
| Calidad de datos | IV | FR-007 | T026 | `api.py:68-98` | `test_api_validacion.py` | ⚠️ (mensajes sin rango completo; lote y presupuesto no existen) |
| Equidad | V | FR-008 | T005, T010 | `features.py:68`, `api.py:23` | `test_features.py`, `test_api_validacion.py` | ✅ (sin prueba a nivel de modelo, T097) |
| Costo de campaña | I | FR-009 | T027–T031 | — | — | ❌ |
| Ingresos retenidos | I | FR-010 | T032–T036, T074, T084 | solo `metricas.py:64` (ventana en memoria) | — | ❌ |
| Costo de campaña, ROI | I | FR-011 | T037–T041 | solo conteo en `evaluate.py:24` | — | ❌ |
| Costo de campaña | I, IV | FR-012 | T037–T041, T080 | — | — | ❌ |
| Operación | VI | FR-013 | T043, T046 | `api.py:126` | `test_api.py:65`, `test_api_predict.py` | ✅ |
| Riesgo de cambio en los datos | I | FR-014 | T048–T055 | `drift.py` (sin `POST /drift`) | `tests/unit/test_drift.py` | ⚠️ |
| Privacidad | IV | FR-015 | T042–T047 | `registro.py` (no se llama desde `api.py`) | `tests/unit/test_registro.py` (solo unidad) | ⚠️ |
| Reproducibilidad | III | FR-016 | T004, T009, T015 | `dataset.py`, `train.py`, `features.py` | `test_dataset.py`, `test_train.py` | ⚠️ (el CSV no sale del generador) |
| Uso responsable | VII | FR-017 | T018, T076, T099 | (ninguna ruta escribe) | sin prueba de rutas | ⚠️ |
| Recall, precision, ROC-AUC; equidad | I, V | FR-018 | T011, T015, T082 | `train.py`, `evaluate.py` | `test_evaluate.py`, `test_train.py` | ⚠️ (sin precision por grupo ni reparto del 5 %) |
| Ingresos retenidos; cambio de datos | IV, VII | FR-019 | T056–T060 | `dashboard/index.html` (no se sirve) | — | ❌ |
| Seguridad | IV | FR-020 | T069, T077, T078 | — | — | ❌ |
| Seguridad, gobernanza | IV, VI | FR-021 | T070, T079 | — | — | ❌ |
| Seguridad, privacidad | IV | FR-022 | T071, T080 | `api.py:91-112` | `test_api_validacion.py`, `test_api_predict.py` | ✅ |
| Privacidad | IV | FR-023 | T072, T081 | `registro.py:37-44` (6 campos, sin retención) | `test_registro.py` | ⚠️ |
| Equidad | V | FR-024 | T073, T083 | — (no hay `revision_proxies`) | — | ❌ |
| Equidad | V | FR-025 | T087 | `docs/AUDITORIA_EQUIDAD.md` no existe | — | ❌ |
| Tasa de cancelación | I | SC-001 | T020 | `api.py` | `test_api_predict.py` | ✅ |
| Calidad de datos | IV | SC-002 | T025 | `api.py` | `test_api_validacion.py` | ✅ |
| Operación | I | SC-003 | T098, T027 | `/predict` ≈ 2,6 ms (p50, medido) | sin prueba de tiempo; el lote no existe | ⚠️ |
| Recall, precision, ROC-AUC | I | SC-004 | T015, T095 | `train.py:97-104` | `test_train.py` | ⚠️ (3 de los 5 criterios de la constitución I) |
| Privacidad | IV | SC-005 | T044 | — (la API no escribe el registro) | — | ❌ |
| Equidad | V | SC-006 | T025, T097 | `api.py:23` | `test_api_validacion.py` | ✅ |
| Costo de campaña | I | SC-007 | T038 | — | — | ❌ |
| Ingresos retenidos | I | SC-008 | T032, T033 | — | — | ❌ |
| Cambio de datos | I | SC-009 | T048–T050 | `drift.py` | `test_drift.py` (sin API) | ⚠️ |
| Equidad | V, VI | SC-010 | T073, T082 | `train.py:96-104` (brecha 0,147) | `test_train.py` | ⚠️ (mide y marca, no se hace cumplir) |

**Requisitos sin prueba:** FR-003 (términos prohibidos), FR-009 a FR-012, FR-017 (rutas), FR-019 a FR-021, FR-024, FR-025, SC-005, SC-007, SC-008.
**KPI sin requisito:** «Costo por cliente retenido» (ASUM-DM §1.2) y el criterio «ROI ≥ 3» no tienen FR ni SC; solo los toca T095 (constitución I los exige).
**Tareas sin requisito propio:** T001, T016, T061 (Dockerfile, «no es requisito de ningún FR»), T066, T067, T068 (constitución VI), T101, T102.
**Código sin tarea:** `tareas.py` y `Makefile`; `src/churn/metricas.py` (solo se cita bajo T058, no está en la estructura del plan); `ratio_impacto_dispar` en `evaluate.py:62` (T100); `perfil_referencia` dentro del model card (el plan pide `data/processed/referencia_entrenamiento.json`); `scripts/instalar_*`.
**Tareas con casilla desactualizada:** solo T004, T009 y T067 están marcadas `[x]`, pero existe código y pruebas para unas 30 más (T101).
**Archivos del plan que no existen:** `model_card.py`, `schemas.py`, `predictor.py`, `campana.py`, `limitador.py`, `Dockerfile`, `docs/AUDITORIA_EQUIDAD.md`, `data/processed/referencia_entrenamiento.json`, `reports/metrics/ultimo_lote.json`, y las pruebas `test_config`, `test_model_card`, `test_schemas`, `test_predictor`, `test_predictor_lote`, `test_recomendaciones`, `test_campana`/`test_contactos`, `test_limitador`, `test_integridad_modelo`, `test_equidad`, `test_api_lote`, `test_api_campana`, `test_api_salud`, `test_api_registro`, `test_api_drift`, `test_api_vista`, `test_api_errores`, `test_api_rutas`, `test_dashboard_html`.

---

## 4. Hallazgos por severidad

### 🔴 Bloqueantes (5)

**B1 · Cuatro rutas del spec no existen.** `/predict/lote`, `/campana/contactos`, `/drift` y `/dashboard` dan 404; `openapi.json` solo trae `/predict`, `/health`, `/metrics`.
- Evidencia: `src/churn/api.py:115,126,139` (únicas rutas); paso 6 de la Fase 2; `curl` → 404.
- Efecto: no se cumplen FR-009, FR-010, FR-011, FR-012, FR-019, la parte API de FR-014, ni SC-003 (lote), SC-007, SC-008, SC-009. `scripts/simular_trafico.py:33` y `tareas.py:18` (`trafico`) no pueden funcionar.
- Cambia: **código** (US3, US4, US5, US7 y Fase 10 de `tasks.md`). El spec y las tareas ya lo cubren.

**B2 · El registro de predicciones no está conectado a la API.** `Registro` está probado en unidad, pero `api.py` nunca lo importa; `logs/` queda vacío tras 73 predicciones.
- Evidencia: `grep registro src/churn/api.py` sin resultados; `logs/` solo tiene `.gitkeep`; `docs/GOBERNANZA.md:56` y `README.md:267` lo admiten «pendiente».
- Efecto: FR-015, FR-023 y SC-005 no se pueden verificar en el servicio (tampoco hay prueba `test_api_registro.py`).
- Cambia: **código** (T047) y la prueba T044.

**B3 · El CSV de entrenamiento no sale del generador, y eso invalida la línea base de drift.** `python -m churn.dataset` genera churn 24,7 % y 9 columnas; el CSV en disco tiene 25,5 % y la columna `periodo`. `dataset.py:127-130` nunca lo sobrescribe sin `--forzar`.
- Evidencia: paso 2; `head data/raw/churn_telco.csv`; `drift.json` → `simulacion.base.informe`: `estado_general=critico` con el escenario «base»; recall 0,602 y ROC-AUC 0,728 (< 0,75) del modelo sobre `generar(seed=43, "base")`; en «crisis» el recall sube a 0,735.
- Efecto: un lote «igual al de entrenamiento» no sale estable (SC-009), la comparación base → crisis es engañosa y FR-016 (reproducibilidad del dato) no se cumple. T096 ya lo anota.
- Cambia: **código/datos** según la decisión D6.

**B4 · `scripts/smoke_test.py` falla.** Es el comando de verificación de `AGENTS.md`.
- Evidencia: línea 91 `h.get("status") == "ok"`, pero `/health` devuelve `{"estado": "sano", …}` (`api.py:44-50`); línea 83 llama `entrenar()` sin el DataFrame obligatorio (`train.py:79`), así que fallaría con `TypeError` si el modelo no existe. Salida real: `[FALLA] API /health`.
- Origen: el prompt P4.1 (`PROMPTS_OPENCODE.md:168`) pide `status ok/degradado`; el spec manda `sano/no_sano`.
- Cambia: **código** (`smoke_test.py`), y de paso el prompt P4.1.

**B5 · SC-010 no se cumple.** Brecha de recall entre grupos de edad de 0,147 (`18-25` 0,797 vs `60+` 0,650) frente al máximo de 0,05; el grupo `60+` tiene 133 clientes (el mínimo es 100).
- Evidencia: `models/model_card.json` → `equidad.dif_max_recall`; `criterios_cumplidos.equidad_recall=false`.
- Efecto: el modelo no es promovible. Es una decisión suya (D2, D3), no solo un arreglo de código.
- Cambia: spec, código o ambos, según la decisión.

### 🟠 Importantes (11)

**I1 · Los criterios de promoción no coinciden entre artefactos.** Constitución I y ASUM-DM §6: recall, precision, precision@250, ROC-AUC y ROI ≥ 3. Spec FR-018/SC-004: solo recall, precision y ROC-AUC. Código: esos tres más equidad y tamaño de grupo (`train.py:97-104`). Nada calcula precision@250/@5 % ni ROI (`evaluate.py` no tiene top-k). D-09 y D-10 siguen abiertas (`research.md:58-68`).
- Cambia: **spec** (FR-018/SC-004) y luego **código** (T095, T065). Ver D1 y D5.

**I2 · Se sirve un modelo no promovible y `/health` dice «sano».** `api.py:134-136` devuelve `estado="sano"` con `aprobado_para_despliegue=False`; ningún código lee `aprobacion` (`grep aprobacion src` solo lo escribe `train.py:119`).
- Hipótesis «aprobado calculado automáticamente»: **confirmada en parte.** `train.py:118` lo calcula solo, pero `docs/GOBERNANZA.md:26-27` lo define como «compuerta técnica», y `data-model.md:127` exige además `aprobacion`. El nombre del campo induce a error y no hay mecanismo que impida servir el modelo (T089). Constitución VI y VII (supervisión humana) quedan solo en papel.
- Cambia: **tareas/spec** (decidir) y **código**. Ver D2.

**I3 · Regla de calibración del umbral incompleta.** `calibrar_umbral` (`train.py:41-52`) toma el umbral de mayor precision con recall ≥ 0,70 y lanza `RuntimeError` si ninguno alcanza el recall (no deja model card). No exige precision ≥ 0,40 al calibrar, aunque ASUM-DM §6 dice «se elige el que cumpla recall y precision». Si ningún umbral cumple los tres criterios, el comportamiento es «entrenar, marcar `criterios_cumplidos` falso y seguir», sin regla escrita. El umbral calibrado (0,538) tampoco coincide con `UMBRAL_RIESGO_MEDIO=0,50` (`config.py:72`) ni con el «0,50 por defecto» del ASUM-DM:35,92.
- ROC-AUC no depende del umbral, así que no entra en la calibración. Ver D4.

**I4 · El model card no sigue el modelo de datos.** Faltan `hash_modelo` (SHA-256 del `.joblib`, base de FR-021), `revision_proxies` (FR-024), precision y reparto del 5 % por grupo (FR-018) y la precision en el 5 % de mayor riesgo. Nombres distintos: `umbral` / `umbral_decision`, `metricas_test` / `metricas`, `equidad` / `metricas_por_grupo_edad`, `logreg` / `logistic_regression`. Hay `hash_dataset` (prompt P3.e) en vez de `hash_modelo`.
- Evidencia: claves de `model_card.json` frente a `data-model.md:113-125`. Cambia: **código** o **data-model** (T090).

**I5 · Sin límite de solicitudes ni comprobación de integridad.** FR-020 (60 por minuto) y FR-021 (huella del modelo): 71 solicitudes seguidas devolvieron 200; `predict.cargar_modelo` (`predict.py:15-23`) no compara ningún hash.
- Cambia: **código** (T077–T079) y pruebas T069, T070.

**I6 · Equidad: faltan FR-024 y FR-025.** No hay comparación del modelo con y sin `metodo_pago`, `tipo_plan`, `antiguedad_meses`, ni `docs/AUDITORIA_EQUIDAD.md`. Es una obligación de la constitución V («revisión de proxies … en el model card»).
- Cambia: **código** (T083) y **docs** (T087).

**I7 · El dashboard no es compatible con `/metrics` y no escapa texto.** `index.html:48-69` lee `modelo.algoritmo`, `modelo.umbral_decision`, `negocio.pct_en_riesgo`, `latencia_p95_ms`, `drift.estado_global`, `drift.features`; el `/metrics` real devuelve `modelo.version`, `modelo.umbral`, `latencia_ms.p95` y no trae `drift`, `ultimo_resumen` ni `ultimo_cambio_datos` (`metricas.py:35-46`). Además inserta con `innerHTML` valores sin escapar (líneas 61, 69, 70), contra FR-019 («texto, nunca contenido ejecutable»).
- Cambia: **código** (T058–T060) y prueba T057.

**I8 · Los prompts del taller se contradicen con las tareas.**
- *IDs distintos y repetidos:* los prompts usan T004 dataset, T006 features, T007 evaluate, T008 train **y** T008 model card, T010–T013 API, T014 pruebas, T018 health, T019 logging, T020 métricas, T021 drift, T024 README (`PROMPTS_OPENCODE.md:80-190`). En `tasks.md` esos números son otras cosas (T008 = `test_schemas`, T015 = train, T045 = registro, T051 = drift). T008 aparece dos veces en los prompts (líneas 99 y 114).
- *Orden imposible:* P3.c (train, línea 99) va antes que P3.d (evaluate, línea 106) y `train.py` importa `evaluate`.
- *Prueba antes que implementación:* P2.6 lo pide y `tasks.md:12` lo exige, pero P3.a–P3.f generan el código y las pruebas llegan al final en P3.g (línea 134, `tests/test_api.py`). **Confirmado.**
- *Archivos sin creador:* `src/churn/predict.py` (usado en P3.f:130, no lo crea ningún prompt; `tasks.md` lo llama `predictor.py`), `src/churn/config.py` (existe en la plantilla; ningún prompt añade las constantes nuevas), `reports/metrics/evaluacion.json` (lo escribe `train.py:142` pero ningún prompt ni tarea lo pide). `scripts/simular_trafico.py` y `dashboard/index.html` **sí existen** (versionados en la plantilla); la hipótesis queda descartada para ellos, con la salvedad de B1 e I7.
- *Contradicciones de contenido:* P3.f:127 pide que `/predict` devuelva `id_cliente` (FR-011/`api.py:32` dicen que no se devuelve); P4.1 pide `status ok/degradado` (spec: `estado sano/no_sano`); P4.2 pide `monitoring.py`/`Monitor` con `id_cliente_hash` y `features` en el log (FR-023: solo 5 campos y sin datos del cliente; el código usa `registro.py`/`id_codificado`); los prompts apuntan a `specs/001-api-churn/tasks.md`, que no existe (líneas 8, 48, 68, 76, 151-152).
- Cambia: **prompts** (y `tareas`, si se decide D7).

**I9 · Trazabilidad y pruebas por debajo de la constitución II.** Solo 3 de 102 tareas marcadas; 20 de los archivos de prueba del plan no existen (sección 3); 11 requisitos sin ninguna prueba. La constitución II exige «al menos una prueba» por requisito.
- Cambia: **tareas** (T101) y **código/pruebas**.

**I10 · La constitución quedó desactualizada.** Línea 20: «`specs/001-api-churn/{spec,plan,tasks}.md`» como fuente de verdad (la 001 está reemplazada y no tiene plan ni tareas; `AGENTS.md` ya apunta a la 002 gracias a T067). Líneas 1-16: el «Sync Impact Report» temporal que debía eliminarse antes del commit sigue ahí.
- Cambia: **constitución** (enmienda PATCH, con su aprobación).

**I11 · Catálogo de recomendaciones provisional y sin vigilancia.** `recomendaciones.py:3` es `TODO(retencion)`; no existe la lista de términos prohibidos ni su validación (T086) ni las pruebas T018/T076. Depende de Retención y Legal (T064).
- Cambia: **código** (T086) y paso externo (T064).

### 🟡 Menores (12)

**M1 · README desactualizado.** Dice «80 pruebas» (líneas 25, 62, 201; real: 106). Marca `/health` y `/metrics` como «pendiente» (27, 247) aunque existen (`api.py:126,139`). La línea 1 manda a `referencia/`, que no existe. Línea 126: «crea `.opencode/commands/speckit.*`»: no existe (ver M2). Línea 175 muestra «churn 24.7 %» sin aclarar que el CSV tiene 25,5 %.
**M2 · Comandos de Spec Kit.** La integración instalada es `claude` con separador `-` (`.specify/integration.json`, versión 1.3.3.dev0), así que los comandos son `/speckit-constitution`, `/speckit-converge`, etc., y están en `.claude/skills/`. Los prompts usan `/speckit.xxx` y el README asume la integración `opencode` (`.opencode/` solo tiene `skills/`). **`/speckit.converge` sí existe** (como `speckit-converge`), así que esa hipótesis queda descartada; lo que no coincide es el nombre y la herramienta.
**M3 · `uv sync` sin `--extra dev` quita `pytest`.** Los docs siempre indican `--extra dev`, pero un `uv sync` a secas rompe `uv run pytest`. Considerar `[dependency-groups]` o documentarlo junto al comando.
**M4 · Atajos rotos en macOS.** `Makefile:3-12` llama `python tareas.py …` (solo existe `python3`); `tareas.py:11` usa `sys.executable`, no `uv run`, así que exige las dependencias en el intérprete del sistema.
**M5 · `simular_trafico.py:36` captura `URLError`**, y `HTTPError` es subclase: un 404 se muestra como «No se pudo conectar».
**M6 · JSON malformado** devuelve `{"campo": "5", "mensaje": "valor no válido"}` (`api.py:95` toma `loc[1:]` y para `json_invalid` queda la posición del carácter).
**M7 · Mensajes de validación.** `debe ser menor o igual que 120` no nombra el rango completo (US2, escenario 1); la lista de categorías sale `'a', 'b' or 'c'` con «or» en inglés (T092). Los límites están duplicados en `api.py:25-31` y `dataset.py:20-23` en vez de `config.py` (T091). Coinciden numéricamente con el spec (1–120, 10–1.000, 0–6, 0–1.000, categorías de `config.py`).
**M8 · Latencia y ROI de `/metrics`.** `api.py:118-122` mide solo `puntuar`, sin validación ni serialización; los p50/p95 (2,6 y 3,0 ms) son sobre una ventana de 1.000 en memoria. El `roi_esperado` de `metricas.py:75` (tasa de éxito × prob × cargo × 6) no es el ROI incremental del ASUM-DM §1.2; el docstring lo advierte.
**M9 · `ratio_impacto_dispar`** (`evaluate.py:62`) no aparece en spec, ASUM-DM ni constitución; solo en `docs/ETICA.md:8` (≥ 0,80) y el prompt P3.d. No entra en `criterios_cumplidos`. Ver D3.
**M10 · Otros documentos que aún apuntan a la 001:** `.opencode/skills/spec-code-review/SKILL.md:13`, `docs/PLAN_B.md:69-72`.
**M11 · Higiene del repo.** Casi todo `src/`, `tests/`, `specs/`, `.specify/` y `business/` está sin versionar; `models/*.joblib`, `reports/` y `data/processed/` no están en `.gitignore` (T102). No hay `Dockerfile` (opcional, T061).
**M12 · Revisión por pares del ASUM-DM** sin firmar (`ASUM-DM.md:9`) y 39 casillas del checklist `seguridad-privacidad-equidad.md` sin marcar. Son requisitos de la salida a producción (ASUM-DM §8, constitución VI).

### Hipótesis de la Fase 4 y Fase 5: veredicto

| Hipótesis | Veredicto y evidencia |
|---|---|
| Archivos usados sin creador | Confirmado para `predict.py` y `evaluacion.json`; `config.py`, `simular_trafico.py` y el dashboard existen (plantilla). Ver I8. |
| T008 repetido / evaluación después del entrenamiento | Confirmado en los prompts (líneas 99, 106, 114). En `tasks.md` no hay IDs repetidos y las dependencias son coherentes (T011 antes de T015). |
| Prueba antes que implementación | Contradicho por los prompts P3.a–P3.g; `tasks.md:12` la exige. I8. |
| Aprobación vs `aprobado_para_despliegue` | Confirmado en parte. I2. |
| Lote mensual, presupuesto, clientes e ingresos, dashboard sin implementar | Confirmado. B1. (`metricas_negocio` calcula conteos, no hay selección de 250.) |
| `rango_edad` excluido del predictor | **Descartado el problema:** `FEATURES` no lo contiene (`config.py:39`), `construir_preprocesador` usa `remainder="drop"` (`features.py:70-75`), la API lo rechaza como campo no previsto y el card lista 7 features. Solo se usa en `metricas_equidad` (`train.py:94`). |
| Umbral de equidad sin valor | Parcial: el valor 0,05 existe (`config.py:68`, SC-010) pero «a confirmar por el dueño» (`ASUM-DM.md:91`). El *ratio de impacto dispar* no tiene criterio en el spec. M9, D3. |
| Calibración con tres criterios | Ver I3. |
| Privacidad en logs/errores | Sin `id_cliente` en claro en errores (422 verificados), `/metrics` ni `drift.json`. El registro con hash existe pero no se usa (B2). `log.error(…, exc_info=exc)` (`api.py:110`) escribe el error interno al log del servidor, no a la respuesta. |
| Validación vs `config.py`/spec | Coinciden. M7. |
| `/speckit.converge` | Existe, con otro nombre. M2. |
| README en macOS | `uv sync --extra dev`, `uv run python -m churn.dataset/train`, `pytest`, `uvicorn` y `curl` funcionan tal cual. Fallan `make …` (M4) y `smoke_test.py` (B4); `instalar_macos.sh` no se ejecutó (instala software). |
| Fuga de datos | **Sin fuga.** Preprocesador dentro del `Pipeline`; umbral calibrado con validación cruzada solo sobre train (`train.py:43-44`); referencia de drift con `X_tr` (`train.py:120`); test evaluado una vez. |
| Reproducibilidad | `config.SEED` en partición, `LogisticRegression`, `RandomForest`, `StratifiedKFold`, `generar` y `df.sample`. Dos entrenamientos: card idéntico salvo la fecha. |
| Lifespan + 503 | Correcto (`api.py:53-62,101-104`; verificado). |
| 422/500 | 422 verificado; 500 genérico definido (`api.py:107-112`). |
| PSI | Fórmula correcta (`drift.py:20-24`), deciles de la referencia guardada (`train.py:55-67`), piso 1e-4. `reclamos_ult_3m` queda con 3 límites tras `np.unique` (valores casi discretos). Referencia dentro del card, no en archivo separado (T052). |
| Formato JSONL | Una línea JSON por predicción, UTF-8; 6 campos (`registro.py:37-44`: añade `latencia_ms`) frente a los 5 de FR-023 y `data-model.md:132-138`; sin retención de 90 días. |
| Latencia p50/p95 | Existe en `/metrics` (M8). |

---

## 5. Plan de corrección (por dependencias)

1. **Decidir D1–D7** (sección 6). Nada de lo siguiente debe empezar sin D1, D4, D5 y D6; el resto puede esperar.
2. **Dato y línea base (B3).** Aplicar D6. *Desbloquea* 8 (drift fiable) y 15.
3. **Alinear artefactos documentales** (en paralelo con 2): enmendar spec FR-018/SC-004 según D1, constitución (I10), nombres del plan según D7, prompts (I8, M2), skill 001 y `PLAN_B` (M10). Después correr `speckit-analyze`/`speckit-converge` para regenerar tareas.
4. **Esquema y model card** (I4): `schemas.py`, `model_card.py`, `hash_modelo`, `revision_proxies`, precision por grupo, precision@5 %/@250 según D5. *Desbloquea* 5, 6 y 9.
5. **Regla de promoción y servicio** (B5, I2, I3): implementar D2 y D4, pruebas T089 y `test_integridad_modelo`. Depende de 4.
6. **Comprobación de integridad y límite de solicitudes** (I5): T077–T079. Depende de 4 (hash).
7. **Rutas de campaña:** `/predict/lote` (T029–T031) → resumen (T034–T036, T074) → `/campana/contactos` (T039–T041). Depende de 4. *Desbloquea* `simular_trafico.py`.
8. **`POST /drift`** y archivo `referencia_entrenamiento.json` (T052–T054). Depende de 2 y 4.
9. **Registro JSONL cableado** (B2): T047, retención y cinco campos (I5/T081). Depende de 7 para registrar el lote.
10. **Dashboard y `/metrics`** (I7): T058–T060 con `ultimo_lote.json` y `drift.json`. Depende de 7, 8 y 9.
11. **`smoke_test.py`** (B4), `simular_trafico.py` (M5), `Makefile`/`tareas.py` (M4) y README (M1). Depende de 7 y 10.
12. **Equidad documentada** (I6): `docs/AUDITORIA_EQUIDAD.md` y T083. Depende de 4.
13. **Pruebas faltantes** (I9) y casillas de `tasks.md` (T101). Se escriben junto a cada paso anterior, no al final.
14. **Pasos externos:** T064 (textos Retención y Legal), T068 (aprobación del dueño), firma de pares del ASUM-DM, checklist de seguridad.
15. **Cierre:** `uv sync --extra dev` → `pytest` → `smoke_test.py` → los 18 escenarios de `quickstart.md` (T066).

**En paralelo:** 2 con 3; 5, 6 y 12 una vez hecho 4; 7 con 8; 11 y 13 durante todo el proceso.

---

## 6. Decisiones que necesitan su criterio

**D1 · ¿Qué criterios de promoción mandan?** Constitución I + ASUM-DM §6 (5 criterios) frente a spec FR-018/SC-004 (3) y código (3 + equidad).
- (a) Enmendar el spec para incluir precision@250 (o @5 %) y ROI ≥ 3. (b) Enmendar constitución y ASUM-DM a 3 criterios. (c) Dejar los 3 en la compuerta y reportar los otros dos solo como informativos.
- **Recomiendo (a):** la constitución y el ASUM-DM mandan por precedencia, y precision@250 es lo que se contacta en la práctica. Depende de D5.

**D2 · ¿Qué se hace con un modelo que no pasa equidad (brecha 0,147)?**
- (a) El servicio se niega a cargarlo (503), salvo una variable de entorno explícita para el taller. (b) Lo sirve, pero `/health` y el dashboard muestran «no aprobado» de forma visible, y la promoción es un paso manual documentado (lo que hoy dice `GOBERNANZA.md`). (c) Mejorar el modelo (otro umbral, revisar proxies como `metodo_pago`) antes de decidir.
- **Recomiendo (b) ahora y (c) como trabajo siguiente:** es un taller sin producción, pero `estado` no debe decir «sano» sin más. Nombre más claro para el campo: `compuerta_tecnica_ok`.

**D3 · ¿Se conserva el umbral de equidad de 0,05 y el *ratio de impacto dispar*?** La brecha con 133 clientes en `60+` es muy ruidosa, y el ratio (≥ 0,80) solo está en `docs/ETICA.md`.
- (a) Mantener 0,05 y añadir el ratio al spec con su umbral. (b) Mantener 0,05 y quitar el ratio (T100). (c) Cambiar el criterio a un intervalo de confianza.
- **Recomiendo (a):** `ETICA.md` ya lo promete y el código ya lo calcula; solo falta un requisito y una prueba.

**D4 · Si ningún umbral cumple recall, precision y ROC-AUC a la vez.**
- (a) El entrenamiento falla y no guarda el modelo. (b) Guarda el modelo con `criterios_cumplidos` falsos y no promovible (hoy, salvo que ni el recall se alcance, que aborta). (c) Prioriza el recall y reporta el resto.
- **Recomiendo (b) en todos los casos:** que `calibrar_umbral` no lance `RuntimeError`, sino que devuelva el umbral de mayor recall posible; así siempre queda evidencia en el card. Además, decidir si los niveles `medio/alto` se derivan del umbral calibrado (0,538) o siguen fijos en 0,50/0,70.

**D5 · D-09 y D-10 (abiertas en `research.md`).** (D-09) ¿La selección de 250 contactos es sobre un lote de 1.000 o sobre toda la base (5.000)? (D-10) ¿precision@250 se mide como 5 % del conjunto de prueba?
- **Recomiendo** lo que ya propone el research: D-09 (a) subir a 5.000 solo para contactos; D-10 confirmar el 5 %.

**D6 · ¿Qué dato es el de verdad?** CSV en disco (25,5 %, con `periodo`; coincide con las cifras del ASUM-DM) o salida del generador (24,7 %).
- (a) Regenerar con `--forzar` y actualizar las cifras del ASUM-DM. (b) Mantener el CSV como fuente de verdad (dato de entrada, no generado) y construir el escenario «base» de drift a partir de él, con «crisis» como transformación de ese mismo base. (c) Ajustar el generador hasta que reproduzca el CSV.
- **Recomiendo (b):** respeta el ASUM-DM (fuente nº 1), arregla la línea base de drift sin tocar las métricas del modelo y se documenta que `churn_telco.csv` es un insumo.

**D7 · Nombres: `predict.py` / `Cliente` en `api.py` (código) frente a `predictor.py` / `ClienteEntrada` en `schemas.py` (plan y tareas).** (T093)
- (a) Renombrar el código. (b) Enmendar plan, tareas y GOBERNANZA al nombre actual.
- **Recomiendo (b) para `predict.py`** (menos cambio y ya lo citan README y GOBERNANZA) **y (a) para `schemas.py`**, porque las rutas nuevas (lote, contactos) reutilizarán los modelos.

**D8 · Contrato de `/health`.** Spec: `estado: sano/no_sano`. Prompt P4.1 y `smoke_test.py`: `status: ok/degradado`. **Manda el spec**; corregir prompt y smoke test (sin alternativa real, solo para dejar constancia).

**D9 · Herramienta de Spec Kit del taller.** El repo tiene la integración `claude` (`/speckit-*`, `.claude/skills`) pero el README, los prompts y `opencode.json` hablan de OpenCode (`/speckit.*`, `.opencode/commands`).
- (a) Instalar también la integración `opencode` y mantener los prompts. (b) Cambiar prompts y README a `/speckit-*` con la integración `claude`.
- **Recomiendo (a)** si el taller es con OpenCode (modelos locales), pero es una decisión de la facilitación.

**D10 · Meta de −3 pp (ASUM-DM:37, abierta).** 250 contactos al mes mueven la tasa ≈ 1,1 pp (la cifra inicial de 0,6–0,7 pp usaba precision 0,40–0,49 en vez de la del top 5 %; ver ASUM-DM §1.4). Sigue pendiente su decisión (subir presupuesto, ampliar la base o redefinir la meta). No se tocó.

---

## 7. Seguimiento de las correcciones

Estado de cada hallazgo tras cada etapa de `docs/DECISIONES.md`. ✅ resuelto · ⚠️ parcial · ⏳ pendiente.

### Etapa 0 · Alinear artefactos (solo documentos, sin código)

| Hallazgo | Estado | Evidencia |
|---|---|---|
| I10 · Constitución desactualizada | ✅ | `.specify/memory/constitution.md` 2.0.1: fuente de verdad = 002 y se eliminó el «Sync Impact Report» temporal |
| I1 · Criterios 5 frente a 3 | ⚠️ | Spec FR-018 y SC-004 ya listan los 5 (D1); falta código y pruebas (T116–T121) |
| I8 · Prompts frente a tareas | ⚠️ | Tabla de IDs corregidos al inicio de `prompts/PROMPTS_OPENCODE.md`; los prompts no se reescribieron |
| I9 · Trazabilidad de tareas | ⚠️ | `tasks.md` con IDs únicos T001–T135 y Fase 14 por etapas; casillas por reconciliar (T134) |
| B3 · CSV frente a generador | ⚠️ | Decidido D6 y especificado (FR-014, FR-016, SC-009); falta código (T105–T108) |
| B5, I2, I3 · Equidad, servir modelo no aprobado, umbral | ⚠️ | Decididos D2–D4 y especificados (FR-026 a FR-028, SC-010); falta código (T118–T125) |
| M2 · Spec Kit | ⚠️ | D9 decidido; falta documentarlo en el README (T131) |
| Hallazgos con decisión de nombres (T093) | ✅ | D7: el plan y las tareas ya usan `predict.py` y `Cliente` en `api.py` |

Todos los demás hallazgos siguen ⏳ y se atacan en las etapas 1 a 4.

### Etapa 1 · Bloqueantes: funcionar de punta a punta

| Hallazgo | Estado | Evidencia |
|---|---|---|
| B1 · Rutas faltantes | ✅ | `POST /predict/lote`, `POST /campana/contactos`, `POST` y `GET /drift` y `GET /dashboard` en `src/churn/api.py`; `src/churn/campana.py`; `predict.puntuar_lote`. `curl`: `/health`, `/metrics`, `/dashboard`, `/drift` → 200 |
| B3 · CSV frente a generador / línea base de drift | ✅ | D6 en `drift.simular` (referencia = split de entrenamiento del CSV, base = split de prueba, crisis = `dataset.aplicar_crisis`). `python -m churn.drift --escenario base` → `estable`, PSI máx. 0,017 |
| B4 · `smoke_test.py` | ✅ | `verificar_api` con el contrato `estado == "sano"`; `smoke_test.py --sin-ia` → «Todo listo para el taller.», código de salida 0 |
| I7 · Dashboard desalineado y sin escapar | ✅ | `dashboard/index.html` lee `/health` y `/metrics` con las claves reales, usa `textContent` y no `innerHTML`; `tests/unit/test_dashboard_html.py` |
| M5 · Mensaje engañoso de `simular_trafico.py` | ✅ | `HTTPError` se informa como HTTP; `tests/unit/test_simular_trafico.py` |
| FR-009, FR-010, FR-011, FR-012, FR-019, SC-003 (lote), SC-007, SC-008, SC-009 | ✅ | `tests/integration/test_api_lote.py`, `test_api_campana.py`, `test_api_drift.py`, `test_api_vista.py`; `tests/unit/test_campana.py` |
| FR-014 (API) | ✅ | `POST /drift` y `GET /drift`; `tests/integration/test_api_drift.py` |

Notas de la etapa:
- **Crisis sobre el CSV:** `reclamos_ult_3m` pasa a crítico (PSI 3,27) y `cargo_mensual` a alerta (0,227); estado general crítico (SC-009). Para la prueba pedí «al menos alerta» en `cargo_mensual`; no se tocó ningún criterio del spec.
- **Límite de la simulación:** la crisis cambia solo las variables, no las etiquetas de churn, así que el recall *sube* (0,734 → 0,868) y la precision baja (0,493 → 0,399); `alerta_recall` no se activa. Mide el efecto de la crisis sobre las entradas del modelo, no un churn nuevo.
- **Sin cambios:** el modelo sigue sin cumplir la equidad (B5), la API aún no escribe el registro (B2) y no hay límite de solicitudes ni integridad (I5): son las etapas 2 y 3.

### Etapa 2 · Gobernanza y equidad

| Hallazgo | Estado | Evidencia |
|---|---|---|
| I1 · Criterios 5 frente a 3 | ✅ | `train.py` evalúa recall, precision, precision en el 5 %, ROC-AUC y ROI ≥ 3 (+ equidad); `evaluate.precision_en_top` y `roi_estimado`; `tests/unit/test_evaluate.py`, `tests/integration/test_train.py` |
| I3 · Regla del umbral | ✅ | `train.elegir_umbral` (FR-027): ya no aborta; guarda `regla_umbral`; `tests/integration/test_train_umbral.py` prueba ambos caminos |
| I2 · Modelo no aprobado servido sin aviso | ✅ | Decisión D2: `/predict` y `/predict/lote` traen `alerta_equidad`; `/health` trae `aprobado_para_despliegue` y `alertas` (`estado` sigue siendo salud operativa); `tests/integration/test_api_alerta_equidad.py`; promoción manual en `docs/GOBERNANZA.md` |
| M9 · Ratio de impacto dispar | ✅ | Condición de aprobación ≥ 0,80 (`criterios_cumplidos.ratio_impacto_dispar`); hoy 0,903 |
| I4 · Model card frente al data-model | ⚠️ (cerrado en la Etapa 3) | Hecho: `regla_umbral`, `criterios_cumplidos` (8), `razones_no_aprobado`, `revision_proxies`, `precision_top`, `roi_estimado`, precision y reparto del 5 % por grupo. Falta `hash_modelo` (Etapa 3, T128–T129) |
| I6 · FR-024 / FR-025 | ⚠️ | FR-024 ✅ (`revision_proxies` en el card y `churn.mitigacion`). FR-025 (`docs/AUDITORIA_EQUIDAD.md`, T087): cerrado en la Etapa 4 |
| B5 · SC-010 (brecha de recall ≤ 0,05) | ⚠️ **Abierto, justificado** | Sigue en 0,147 (18-25: 0,797; 60+: 0,650). Por D2 se sirve como no aprobado, con alerta; el criterio no se relajó. Ver el intento de mitigación abajo |

**Intento de mitigación (D2)** — `python -m churn.mitigacion`, `reports/metrics/mitigacion_equidad.json`, mismo split y semilla:

| Variante | Recall | Brecha de recall | Ratio de impacto dispar |
|---|---|---|---|
| Base: regresión logística | 0,734 | **0,147** | 0,903 |
| Sin `metodo_pago` | 0,727 | 0,147 | 0,906 |
| Sin `tipo_plan` | 0,737 | 0,095 | 0,856 |
| Sin `antiguedad_meses` | 0,734 | 0,075 | 0,850 |
| Random Forest | 0,730 | 0,162 | 0,861 |

- **Ninguna variante baja de 0,05** (la mejor es 0,075): se documenta y no se fuerza; el modelo servido no cambia.
- **Proxies de la edad:** la asociación de cada variable con `rango_edad` (V de Cramér) es baja: `tipo_plan` 0,134, `cargo_mensual` 0,094, el resto ≤ 0,04. No hay un proxy fuerte que explique la brecha.
- **Ruido:** el grupo `60+` tiene 133 clientes y solo 40 positivos en la prueba (`18-25`: 64); el error estándar de la diferencia entre ambos recalls es ≈ 0,09, así que 0,147 equivale a ~1,6 desviaciones. No prueba que no haya sesgo, pero tampoco permite afirmarlo: hace falta más datos por grupo antes de decidir.
- **Sobre el camino 2 de D4:** con `MIN_RECALL = 0,70` el segundo camino («mayor recall») es prácticamente inalcanzable, porque marcar a todos los clientes da recall 1,0. Se probó forzando `MIN_RECALL` por encima de 1. En la práctica el modelo queda no aprobado por otros criterios, como hoy por la equidad.

Criterios de la constitución con el CSV: precision en el 5 % (k = 62) 0,758; ROI estimado 9,33; los cinco cumplen.

### Etapa 3 · Privacidad y seguridad

| Hallazgo | Estado | Evidencia |
|---|---|---|
| B2 · Registro no conectado a la API | ✅ | `/predict`, `/predict/lote` y `/campana/contactos` escriben `logs/predicciones.jsonl` con `id_codificado`; solo 5 campos (`fecha`, `id_codificado`, `probabilidad_churn`, `nivel_riesgo`, `version_modelo`) y retención de 90 días (`config.RETENCION_REGISTRO_DIAS`). `tests/integration/test_api_registro.py`, `tests/unit/test_registro_campos.py` |
| I5 · Sin límite de solicitudes ni integridad | ✅ | `src/churn/limitador.py` (60 por minuto por IP, 429 con `{"error": …}` y `Retry-After`); `predict.cargar_modelo` compara el SHA-256 del `.joblib` con `hash_modelo` del card **antes** de deserializar. `tests/unit/test_limitador.py`, `tests/integration/test_api_limite.py`, `tests/unit/test_integridad_modelo.py` |
| I4 · Model card frente al data-model | ✅ | `train.guardar_modelo` escribe `hash_modelo` solo en `models/model_card.json` (el `.joblib` contiene el card); `tests/integration/test_train.py` |
| FR-022 · Errores sin valores ni trazas | ✅ | Con un valor centinela en `id_cliente`, plan y tipos, ningún 422/500/503 lo repite ni muestra rutas o trazas: `tests/integration/test_api_errores.py`. Sin cambios de código: el manejador ya lo cumplía |

### Etapa 4 · Menores, documentación y cierre

| Hallazgo | Estado | Evidencia |
|---|---|---|
| M1 · README desactualizado | ✅ | Conteo real de pruebas (325), estado real de las rutas, comandos y salidas ejecutados en macOS, sin referencia a `referencia/`, generador solo para demos (D6) |
| M2 · Comandos de Spec Kit | ✅ | README: tabla `/speckit-*` (Claude Code) frente a `/speckit.*` (OpenCode) (D9) |
| M3 · `uv sync` quita `pytest` | ✅ | `[dependency-groups] dev` en `pyproject.toml`: `uv sync` a secas conserva `pytest`; `--extra dev` sigue funcionando |
| M4 · Atajos rotos en macOS | ✅ | `Makefile` usa `uv run python tareas.py`; `make datos`, `probar`, `drift` y `smoke` ejecutados |
| M6 · JSON malformado | ✅ | `{"campo": "cuerpo", "mensaje": "JSON mal formado"}`; `test_api_errores.py` |
| M7 · Mensajes y límites duplicados | ✅ | «debe estar entre 1 y 120», categorías con «o»; los rangos viven en `config.py` y los usan `api.py`, `dataset.py` y `features.py` |
| M10 · Referencias a la 001 | ✅ | `.opencode/skills/spec-code-review`, `docs/PLAN_B.md` y `prompts/PROMPTS_OPENCODE.md` apuntan a la 002; las menciones que quedan son históricas a propósito |
| M11 · Higiene del repo | ✅ | `.gitignore` ampliado; decisión T102: `models/` y `reports/metrics/` se versionan (README §8, GOBERNANZA §3); `Dockerfile` opcional (construido y probado el 2026-11-07, ver Re-auditoría) |
| I6 · FR-025 | ✅ | `docs/AUDITORIA_EQUIDAD.md` y `tests/unit/test_docs_auditoria_equidad.py` |
| I10, D2, D10 en documentos | ✅ | `docs/GOBERNANZA.md` §9 y `business/ASUM-DM.md` §1.4 y §8 |

---

## 8. Re-auditoría

Fecha: 2026-11-07 · Rama `main`, tras las etapas 0 a 4 · Alcance: repositorio completo, las 5 fases de la auditoría original, contra `specs/002-campana-retencion-monitoreo/`.

**Artefactos que generó esta re-auditoría** (declarados como en la original):
- `python -m churn.train` dos veces sobrescribió `models/` y `reports/metrics/evaluacion.json`; se restauraron desde una copia previa y `git status` no muestra cambios en `models/`, `reports/` ni `data/`.
- Para el escenario 18 se agregó un byte a `models/churn_model.joblib`; se restauró desde la copia (el servicio volvió a `sano`).
- `drift.json` y `ultimo_lote.json` se sobrescribieron con las simulaciones y se restauraron con `git checkout`; se movió `drift.json` unos minutos para ver el 404 de `GET /drift`.
- `logs/predicciones.jsonl` se generó (6.302 líneas en la prueba de escenarios) y se borró. `data/raw/churn_telco.csv` no cambió (md5 `81bced38…` antes y después).
- Se levantó `uvicorn` en el puerto 8000 varias veces y se detuvo cada vez. Copia previa y scripts en el directorio temporal de la sesión.

### Fase 1 · Inventario y fuentes
- Fuente de verdad: `business/ASUM-DM.md` → `.specify/memory/constitution.md` 2.0.1 → `specs/002-…` (la 001 está marcada «Reemplazada»); `AGENTS.md` ya apunta a la 002.
- `src/churn/`: 15 módulos, 1.606 líneas; 41 archivos de prueba; 139 archivos versionados.
- Spec: 28 FR y 10 SC. `tasks.md`: 135 tareas, 129 marcadas; las 6 sin marcar son T007, T012 y T093 (sustituidas u obsoletas por decisión, D7), T064 y T068 (pasos humanos) y T135 (esta re-auditoría).
- `docs/prompts_taller.md` sigue sin existir (el equivalente es `prompts/PROMPTS_OPENCODE.md`).

### Fase 2 · Ejecución real

| # | Comando | Esperado | Obtenido | Antes | Ahora |
|---|---|---|---|---|---|
| 1 | `uv sync` | Entorno listo, conserva `pytest` | `pytest 9.2.0` sigue instalado | ⚠️ | ✅ |
| 2 | `uv run python -m churn.dataset` | Informa y no pisa el CSV | `5000 filas · escenario base · churn 24.7%` + «ya existe; use --forzar»; md5 del CSV igual | ⚠️ | ✅ (documentado: el CSV es fuente de verdad, D6) |
| 3 | `uv run python -m churn.train` (×2) | Métricas ≥ umbrales y reproducible | `logreg · umbral 0.538 · recall 0.734 · precision 0.493 · ROC-AUC 0.811`; los 5 criterios y la razón de no aprobación (brecha 0,147). Dos corridas: el card difiere solo en `fecha_entrenamiento` y `hash_modelo` | ✅/❌ | ✅ técnico / ❌ equidad (abierto, B5) |
| 4 | `uv run pytest` | Todo en verde | `325 passed in 14.47s` (185 unitarias, 132 de integración, 8 de contrato) | ✅ | ✅ |
| 5 | `uv run python -m churn.drift --escenario crisis` | Informe PSI + comparación | `critico`; `reclamos_ult_3m` PSI 3,275 y `cargo_mensual` 0,227; base estable | ⚠️ | ✅ |
| 6 | `scripts/simular_trafico.py --escenario crisis --n 500` | Envía clientes | Sin API: «No se pudo conectar … ¿Está corriendo uvicorn?»; con API: `[ok] 500 clientes (crisis) enviados` | ❌ | ✅ |
| 7 | Rutas de la API | Todas existen | `/predict`, `/predict/lote`, `/campana/contactos`, `/drift` (POST y GET), `/health`, `/metrics`, `/dashboard` responden según contrato | ❌ | ✅ |
| 8 | `uv run python scripts/smoke_test.py --sin-ia` | `Todo listo para el taller.` | 8 comprobaciones de Python en `[OK]` (incluye lote, contactos, drift y dashboard), código de salida 0 | ❌ | ✅ |
| 9 | `make datos` / `probar` / `drift` / `smoke` | Funcionan en macOS | `datos`, `probar` y `drift` bien. `make smoke` (sin `--sin-ia`) falla solo porque el servidor Ollama no está activo en este equipo | ❌ | ✅ (la falla restante es del entorno) |
| 10 | Escenarios 1–17 y 19 de `quickstart.md` contra la API real, con `CHURN_HASH_SALT` | Todos pasan | Pasan los 21 chequeos. En la primera pasada el 19 «antes» dio 200 porque ya existía `reports/metrics/drift.json` (precondición, no defecto); sin ese archivo dio 404 con `{"error": "Aún no hay un informe de cambio de datos"}`. El 18 va en la fila siguiente | ❌ | ✅ |
| 11 | Escenario 18: `.joblib` alterado | `no_sano` y 503 | `GET /health` 503 `"estado":"no_sano"`; `POST /predict` 503 `{"error":"Modelo no disponible"}`; el log del servidor dice «la huella del modelo no coincide con su ficha». Restaurado: `sano` | ❌ | ✅ |
| 12 | 70 solicitudes seguidas a `/health` | Límite de 60 | 59 con 200 y 11 con 429 (había una solicitud previa en la ventana); el 429 trae `retry-after` y `{"error": "Demasiadas solicitudes; reintente en 59 s"}` | ❌ | ✅ |
| 13 | Registro tras los escenarios | Sin ids en claro | 6.302 líneas, todas con las 5 claves; ni `CLI-SECRETO-001` ni ningún `id_cliente` de las 1.000 filas del lote aparece | ❌ | ✅ |

No se ejecutaron: `scripts/instalar_*.sh` (instalan software), y el flujo con Ollama/OpenCode. `docker build -t churn-api .` no se pudo ejecutar en la re-auditoría (el demonio de Docker no estaba activo); después se construyó la imagen sin errores, el contenedor arrancó con `CHURN_HASH_SALT` y `GET /health` respondió.

### Fase 3 · Matriz de trazabilidad (resumen recalculado)
Cada FR y SC de la spec se buscó en los comentarios y docstrings de `tests/`. **37 de 38 tienen al menos una prueba que los cita**; FR-025 (auditoría trimestral) es un procedimiento humano y lo guarda `tests/unit/test_docs_auditoria_equidad.py`. Estados: ✅ en los 28 FR y 10 SC, salvo SC-010 ⚠️ (el criterio se mide y se hace cumplir como compuerta, pero el modelo actual no lo cumple: B5).

| Antes (⚠️/❌) | Ahora |
|---|---|
| FR-009 a FR-012, FR-019, SC-003, SC-007, SC-008 (❌: rutas inexistentes) | ✅ `test_api_lote.py`, `test_api_campana.py`, `test_api_vista.py` |
| FR-015, FR-023, SC-005 (❌/⚠️: registro sin cablear) | ✅ `test_api_registro.py`, `test_registro_campos.py` |
| FR-020, FR-021 (❌) | ✅ `test_limitador.py`, `test_api_limite.py`, `test_integridad_modelo.py` |
| FR-024, FR-025 (❌) | ✅ `test_equidad.py`, `test_mitigacion.py`, `test_docs_auditoria_equidad.py` |
| FR-003, FR-017 (⚠️: sin prueba) | ✅ `test_recomendaciones*.py`, `test_api_rutas.py` |
| FR-018, SC-004 (⚠️: 3 de 5 criterios) | ✅ los 5 criterios en `train.py` y `test_evaluate.py` |
| SC-010 (⚠️) | ⚠️ sigue abierto por el resultado del modelo, no por falta de código |

KPI sin requisito (heredado): «Costo por cliente retenido» sigue sin FR propio; la constitución I lo cubre con precision en el 5 % y ROI ≥ 3.

### Fase 4 · Hipótesis, otra vez

| Hipótesis | Veredicto |
|---|---|
| `rango_edad` fuera del predictor | Sigue descartado el problema: `FEATURES` no lo contiene; la API lo rechaza (422 «campo no previsto»); `test_features.py` y `test_predict.py` comprueban que cambiar solo la edad no altera `predict_proba`. |
| Fuga de datos | Sin fuga (código de entrenamiento sin cambios de lógica: preprocesador dentro del `Pipeline`, umbral por validación cruzada solo en train, test evaluado una vez). |
| Reproducibilidad | Dos entrenamientos: card idéntico salvo `fecha_entrenamiento` y `hash_modelo` (la huella cambia porque el `.joblib` lleva la fecha). |
| Aprobación vs `aprobado_para_despliegue` | Resuelto por D2: `aprobado_para_despliegue` es la compuerta técnica, `aprobacion` queda vacía hasta la firma humana; `/health` y cada predicción lo muestran. |
| Privacidad en logs y errores | Verificado en vivo (escenario 15 y `test_api_errores.py`): sin ids en claro ni valores de entrada; 500 genérico. |
| Lifespan + 503 | Correcto, ahora también por huella inválida. |
| PSI | Sin cambios; base estable, crisis crítica. |
| README en macOS | Todos los comandos documentados se ejecutaron; ver Fase 2. |
| Validación frente a `config.py` | Una sola fuente: los rangos ya no están duplicados. |
| `/speckit.converge` | Existe como `/speckit-converge`; README documenta ambos nombres. |
| Latencia y ROI de `/metrics` | Igual que M8: documentado en el README, no cambiado. |

**Hallazgos nuevos de la re-auditoría** (ambos 🟡, resueltos en la misma etapa):
- **N1.** La ruta de auto-entrenamiento de `scripts/smoke_test.py` guardaba el modelo sin `hash_modelo`; con la comprobación de integridad el servicio habría quedado en 503. Ahora usa `train.guardar_modelo`.
- **N2.** Al ampliar el smoke test a lote, campaña y drift, cada ejecución sobrescribía `reports/metrics/` y `logs/`. Ahora redirige esas rutas a una carpeta temporal.

**Observaciones** (límites de diseño, no defectos; están en el README §8): el límite de solicitudes vive en la memoria de un proceso y usa la IP del socket, así que detrás de un proxy todos comparten IP; si la escritura del registro falla, la predicción responde 500 (se prefiere no responder sin rastro de auditoría).

### Fase 5 · Antes y después por severidad

| Severidad | Hallazgos en 2026-11-06 | Resueltos | Siguen abiertos | Nuevos (resueltos) |
|---|:-:|:-:|:-:|:-:|
| 🔴 Bloqueantes | 5 | 4 (B1, B2, B3, B4) | **1** (B5) | 0 |
| 🟠 Importantes | 11 | 9 (I1–I7, I9, I10) | **2** (I8, I11) | 0 |
| 🟡 Menores | 12 | 10 (M1–M7, M9–M11) | **2** (M8, M12) | 2 (N1, N2) |
| **Total** | **28** | **23** | **5** | 2 |

**Lo que sigue abierto, y por qué:**

| Hallazgo | Justificación | Quién y cuándo se cierra |
|---|---|---|
| **B5** · SC-010: brecha de recall de 0,147 frente a 0,05 | No se resuelve con código. Se intentó la mitigación permitida (D2): ninguna variante bajó de 0,05 (la mejor, 0,075) y el grupo `60+` tiene 40 positivos en la prueba, así que la brecha es ruidosa (≈ 1,6 desviaciones). Relajar el criterio o usar la edad para umbrales por grupo está prohibido (constitución V, D2/D3). El modelo se sirve como **no aprobado**, con alerta en cada respuesta | Dueño del modelo, con más datos por grupo o una decisión explícita; mientras tanto la alerta es visible |
| **I8** · Los prompts del taller contradicen las tareas | Las rutas ya apuntan a la 002 y la tabla inicial mapea cada ID. Lo que queda (orden P3.c/P3.d, P4.1 con `status ok/degradado`, P4.2 con `monitoring.py`) es el guion didáctico del taller: reescribirlo cambia el ejercicio que da la facilitación | Facilitación del taller |
| **I11** · Catálogo de recomendaciones provisional | La lista de términos prohibidos y su validación existen y están probadas (T086, T076). Los textos definitivos los define Retención y los revisa Legal; no se pueden inventar (T064) | Retención y Legal |
| **M8** · Latencia y ROI de `/metrics` | La latencia mide solo la puntuación y el ROI es un estimado; ambos están documentados en el README y en el docstring. Medir la solicitud completa exige un middleware de tiempos y no cambia ninguna decisión | Opcional, sin dueño; cambia si el negocio pide un SLA |
| **M12** · Pares del ASUM-DM sin firmar y 39 casillas del checklist `seguridad-privacidad-equidad.md` | Son aprobaciones humanas de la salida a producción (ASUM-DM §8, constitución VI); marcarlas sin revisión sería falsear la revisión | Dos pares y el dueño del modelo |

Además, **fuera de los hallazgos originales y sin cerrar**: D10 (la meta de −3 pp exige ≈ 800 contactos y ≈ 6.400 USD al mes frente a 250 y 2.000 USD; `business/ASUM-DM.md` §1.4) es una decisión del negocio, y T068 (aprobación del dueño del modelo) es manual.

**Conclusión.** De 28 hallazgos quedan 5, todos con dueño que no es el código. El servicio funciona de punta a punta, cumple los requisitos de privacidad y seguridad con pruebas, y cuenta con 325 pruebas en verde. Su única condición incumplida es la equidad por edad, que está medida, avisada en cada respuesta y documentada.
