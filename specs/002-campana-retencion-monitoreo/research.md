# Research: Riesgo de churn, campaña de retención y monitoreo

Fase 0 del plan. Todas las decisiones técnicas vienen de la instrucción del dueño del proyecto, de la
constitución y de `business/ASUM-DM.md`. No quedaron `NEEDS CLARIFICATION` en el contexto técnico; las
entradas D-09 y D-10 quedaron resueltas el 2026-11-06 (ver `docs/DECISIONES.md`).

## D-01 Modelo: regresión logística primero, Random Forest solo si hace falta

- **Decisión**: `Pipeline` de scikit-learn con `ColumnTransformer` (escalado estándar para las 4 numéricas, one-hot para las 3 categóricas) y `LogisticRegression`. `RandomForestClassifier` solo si la regresión no cumple recall ≥ 0,70, precision ≥ 0,40 y ROC-AUC ≥ 0,75.
- **Razón**: constitución V (modelo simple primero, explicable); el baseline ya se espera ≈ 0,81 de ROC-AUC. Los coeficientes permiten explicar cada predicción al analista.
- **Alternativas**: Random Forest como primera opción (menos explicable); gradient boosting (más dependencias y sin necesidad demostrada).
- **Reproducibilidad**: `random_state=config.SEED` en la partición 75/25 estratificada y en el clasificador.

## D-02 Niveles de riesgo y catálogo de recomendaciones

- **Decisión**: tres niveles derivados de la probabilidad: **alto** (≥ 0,70, `UMBRAL_RIESGO_ALTO`), **medio** (≥ 0,50 y < 0,70, `UMBRAL_DECISION_DEFAULT`) y **bajo** (< 0,50). El catálogo (`recomendaciones.py`) tiene una entrada por nivel. El sistema solo selecciona la entrada; no genera texto.
- **Razón**: la spec exige "una entrada por nivel" y fija solo el umbral de "alto". Reusar los dos umbrales que ya están en `config.py` evita inventar cifras.
- **Pendiente de negocio**: el texto definitivo lo escribe Retención y lo revisa Legal (spec, FR-003). Hasta entonces el plan usa textos provisionales marcados `TODO(retencion)` que no sugieren negar servicios ni cambiar precios; una prueba lo verifica.
- **Alternativas**: dos niveles (alto/no alto): más simple, pero pierde la señal media; nivel por variable dominante: descartado por la spec (catálogo fijo).

## D-03 Validación de entrada: Pydantic v2 con `extra="forbid"`

- **Decisión**: `api.py` define los modelos de entrada (`Cliente`, D7) con `ConfigDict(extra="forbid")`, `Field(ge=, le=)` y `Literal` tomados de `config.py` (`PLANES`, `METODOS_PAGO`, `RENOVACION`). Antigüedad y reclamos son enteros (modo estricto, sin decimales); cargo mensual 10–1.000 USD; uso de datos 0–1.000 GB. Los topes se añaden a `config.py` (`CARGO_MIN`, `CARGO_MAX`, `USO_DATOS_MAX`, `LOTE_MAX = 1000`).
- **Razón**: constitución IV; el mismo `config.py` es la única fuente de dominios (regla de no inventar columnas). `rango_edad` no está en el modelo de entrada, así que llega como campo no previsto y se rechaza.
- **Errores**: un manejador convierte los errores de Pydantic en una respuesta de validación (HTTP 422) con campo, motivo y valores permitidos. En lotes, el mensaje incluye la posición del cliente inválido y el lote completo se rechaza.
- **Alternativas**: validar a mano (más código y más errores); ignorar campos extra (viola la spec y la constitución).

## D-04 Privacidad del registro: hash con sal

- **Decisión**: `registro.py` calcula SHA-256 de `sal + id_cliente` y registra los primeros 16 caracteres hexadecimales en `logs/predicciones.jsonl` (una línea por predicción: marca de tiempo, hash, probabilidad, nivel, versión del modelo). La sal sale de la variable de entorno `CHURN_HASH_SALT`; si no existe, se usa una sal de desarrollo documentada y el servicio avisa en el arranque.
- **Razón**: un hash sin sal de un ID corto se puede revertir por fuerza bruta; la sal lo evita sin servicios externos. Un identificador opcional ausente se registra como `null`, nunca como cadena vacía.
- **Alternativas**: no registrar ID (se pierde trazabilidad); cifrado reversible (exige gestionar claves; innecesario).

## D-05 Cambio de datos: PSI con referencia guardada en el entrenamiento

- **Decisión**: al entrenar se guarda en el model card (`perfil_referencia`, I-11), calculado solo con el split de entrenamiento, para cada una de las 7 variables, los límites de 10 deciles (numéricas) o las proporciones por categoría (categóricas). `drift.py` calcula PSI = Σ (p_nuevo − p_ref) · ln(p_nuevo / p_ref), con piso de 1e-4 en las proporciones para evitar división por cero. Niveles: estable < 0,10; alerta ≥ 0,10; crítico ≥ 0,25 (`PSI_ALERTA`, `PSI_CRITICO` ya en `config.py`).
- **Lote pequeño**: por debajo de 100 filas (`MIN_FILAS_DRIFT = 100`) se responde "datos insuficientes" y no se calcula PSI.
- **Razón**: coincide con spec FR-014 y con el ASUM-DM §7/§8. Los deciles salen del conjunto de entrenamiento, por lo que un lote igual al de entrenamiento da PSI ≈ 0. **D6**: la fuente es `data/raw/churn_telco.csv`; la referencia sale de su split de entrenamiento y vive en el model card (`perfil_referencia`); el escenario "base" es el split de prueba (PSI < 0,10) y "crisis" es una transformación del mismo CSV (cargos y reclamos más altos). El generador queda para demos y pruebas.
- **Alternativas**: prueba de Kolmogorov-Smirnov (no da un umbral de negocio estándar); bibliotecas externas de drift (dependencia nueva sin necesidad).

## D-06 Estado de monitoreo en archivos JSON

- **Decisión**: el servicio es sin estado en memoria entre peticiones. El último resumen de riesgo se guarda en `reports/metrics/ultimo_lote.json` (solo agregados: totales, conteos, ingresos; nunca IDs) y el último informe de cambio de datos en `reports/metrics/drift.json`. `GET /metrics` y la vista los leen.
- **Razón**: FR-019 pide mostrar "el último" resumen e informe; los archivos sobreviven a reinicios y no requieren base de datos (constitución III).
- **Alternativas**: estado en memoria (se pierde al reiniciar); base de datos (dependencia innecesaria).

## D-07 Vista visual: HTML estático sin dependencias

- **Decisión**: se reutiliza `dashboard/index.html` (ya existe). Se sirve en `GET /dashboard`, usa solo `fetch` a `/health` y `/metrics`, JavaScript y CSS en línea, sin CDN ni bibliotecas. Es de solo lectura: no tiene formularios que envíen datos.
- **Razón**: decisión del dueño del proyecto (spec enmendada con FR-019); cumple "sin dependencias" y "sin cuentas".
- **Seguridad**: el HTML debe escapar cualquier texto que venga de las respuestas antes de insertarlo; no muestra identificadores.

## D-08 Docker opcional

- **Decisión**: un `Dockerfile` mínimo (imagen base de Python 3.11, instala el paquete y ejecuta uvicorn). No es requisito de ningún FR ni de las pruebas, y no se usa registro con cuenta.
- **Alternativas**: docker-compose (innecesario con un solo servicio); Kubernetes (prohibido por la constitución).

## D-09 (RESUELTA 2026-11-06) Selección de contactos por lote frente a toda la base

- **Resolución (D5, I-2)**: la selección se hace sobre el lote que se puntúa; `POST /campana/contactos` acepta hasta 5.000 clientes (la base mensual) y se ordena por ingreso esperado (probabilidad × cargo mensual) entre los clientes en riesgo alto, tomando `min(250, clientes en riesgo)`. `POST /predict/lote` conserva 1.000. El texto siguiente es el análisis original.

- **Hallazgo**: la base mensual del ASUM-DM es de 5.000 clientes y el lote máximo es de 1.000. Si el analista puntúa 5 lotes y pide 250 contactos por cada uno, contactaría 1.250 (10.000 USD), no 250.
- **Decisión provisional del plan**: `POST /campana/contactos` recibe un lote de hasta 1.000 clientes y elige los contactos solo dentro de ese lote, con el presupuesto indicado. La selección sobre la base completa exige que el analista pase toda la base en una sola llamada o reparta el presupuesto entre lotes.
- **Para decidir (dueño del proyecto)**: (a) subir el límite solo para la selección de contactos a 5.000; (b) mantener 1.000 y repartir el presupuesto por lote; (c) guardar las puntuaciones de la base mensual y seleccionar sobre todas. Recomendado: (a), porque no cambia el límite de puntuación acordado en la aclaración y preserva el tope de 2.000 USD.

## D-10 (RESUELTA 2026-11-06) Cómo medir precision@250 en la evaluación

- **Resolución (D5)**: precision@k con k = 5 % del conjunto evaluado (equivale a 250 de 5.000); ranking por probabilidad. Pasa a ser el criterio 3 de FR-018. El texto siguiente es el análisis original.

- **Hallazgo**: el conjunto de prueba tiene 1.250 clientes (25 % de 5.000); "los 250 de mayor riesgo" sobre 1.250 es el 20 %, mientras que en la campaña real son 250 de 5.000 (5 %). Medirlo así sobreestimaría la dificultad y no reflejaría la campaña.
- **Decisión provisional del plan**: `evaluate.py` reporta precision en el **5 % de mayor riesgo** del conjunto de prueba (62 clientes), equivalente a 250 de 5.000, además de la precision global.
- **Para decidir (dueño del proyecto)**: confirmar que el 5 % es la referencia. Si la base de producción cambia de tamaño, el porcentaje se recalcula como contactos / base.

## D-11 Calibración del umbral de decisión

- **Decisión**: el umbral de decisión se elige en un conjunto de validación separado del de prueba (validación cruzada estratificada sobre el 75 % de entrenamiento) como el que cumple recall ≥ 0,70 con la mayor precision; el conjunto de prueba solo se usa una vez para el informe final. El umbral elegido se guarda en el model card.
- **Razón**: ASUM-DM §6 ("calibrado en validación"); evita inflar métricas por haber ajustado sobre prueba.

- **Regla del umbral (D4, FR-027)**: el entrenamiento nunca aborta. Primero el umbral de mayor precision con recall ≥ `MIN_RECALL`; si no existe, el de mayor recall. Se guarda siempre `criterios_cumplidos` y `razones_no_aprobado`.

## D-12 Interfaz del servicio (resumen; detalle en `contracts/openapi.yaml`)

| Ruta | Método | FR |
|---|---|---|
| `/predict` | POST | FR-001..008, 015 |
| `/predict/lote` | POST | FR-009, FR-010 |
| `/campana/contactos` | POST | FR-011, FR-012 |
| `/drift` | POST (lote) y GET (último informe) | FR-014 |
| `/health` | GET | FR-013 |
| `/metrics` | GET | FR-010, FR-014, FR-019 |
| `/dashboard` | GET | FR-019 |

Todas las respuestas que contienen predicciones o listas de contacto incluyen `aviso_uso_responsable` (FR-005). Ninguna ruta modifica datos de clientes (FR-017).

## D-13 Intento de mitigación de equidad (D2)

- **Decisión**: un solo intento legítimo, reportado en `reports/metrics/mitigacion_equidad.json`: (a) modelo actual; (b) sin cada variable que pueda sustituir a la edad (`metodo_pago`, `tipo_plan`, `antiguedad_meses`); (c) regresión logística frente a Random Forest. Se informa la brecha de recall y el ratio de impacto de cada variante. `rango_edad` solo audita: no es predictor ni fija umbrales por grupo.
- **Si ninguna variante baja de 0,05**: se documenta y no se fuerza; el modelo servido no cambia por este intento.

## D-14 Alerta de equidad y estado del servicio (D2, D8)

- **Decisión**: con `aprobado_para_despliegue=false`, `Prediccion` y cada elemento de `/predict/lote` llevan `alerta_equidad` (texto con la razón); `/health` agrega `aprobado_para_despliegue` y `alertas` y mantiene `estado` = salud operativa (modelo cargado e íntegro).
- **Razón**: la herramienta apoya con revisión humana; ocultar el estado de aprobación sería peor que servirlo con alerta.
