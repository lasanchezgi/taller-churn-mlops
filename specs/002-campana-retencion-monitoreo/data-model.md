# Data Model: Riesgo de churn, campaña de retención y monitoreo

Entidades de la spec, con campos, reglas de validación y relaciones. Los nombres de columnas son los de
`src/churn/config.py`; no se inventan columnas. Los dominios y límites viven en `config.py` y se
reutilizan en la validación.

## Cliente (entrada de `/predict`, y cada elemento de un lote)

| Campo | Tipo | Regla | FR |
|---|---|---|---|
| `antiguedad_meses` | entero | 1 ≤ x ≤ 120; sin decimales | FR-006 |
| `tipo_plan` | texto cerrado | `prepago`, `pospago_basico`, `pospago_premium` | FR-006 |
| `cargo_mensual` | número | 10 ≤ x ≤ 1.000 (USD) | FR-006 |
| `reclamos_ult_3m` | entero | 0 ≤ x ≤ 6; sin decimales | FR-006 |
| `uso_datos_gb` | número | 0 ≤ x ≤ 1.000 (GB) | FR-006 |
| `metodo_pago` | texto cerrado | `tarjeta_credito`, `debito_automatico`, `efectivo`, `transferencia` | FR-006 |
| `renovo_contrato` | texto cerrado | `si`, `no` | FR-006 |
| `id_cliente` | texto, opcional | solo trazabilidad; hasta 64 caracteres entre letras, números, guion y guion bajo; nunca se registra en claro | FR-015 |

Reglas generales:
- Cualquier otro campo (incluido `rango_edad`) se rechaza como no previsto (FR-007, FR-008).
- Faltante, nulo, tipo incorrecto o fuera de rango se rechaza con mensaje que nombra el campo.
- `id_cliente` no entra al modelo (solo a la trazabilidad).

## Prediccion (salida por cliente)

| Campo | Tipo | Regla |
|---|---|---|
| `probabilidad_churn` | número 0–1 | probabilidad de cancelar en los 60 días siguientes al corte |
| `nivel_riesgo` | `alto` / `medio` / `bajo` | alto ≥ 0,70; medio ≥ 0,50 y < 0,70; bajo < 0,50 |
| `recomendacion` | texto | tomado del `CatalogoRecomendaciones` según el nivel |
| `version_modelo` | texto | versión semántica del modelo servido (FR-004) |
| `aviso_uso_responsable` | texto | fijo (FR-005) |
| `alerta_equidad` | texto, opcional | presente mientras el modelo no esté aprobado, con la razón (FR-026) |

Estado: una predicción es inmutable; la misma entrada y la misma versión del modelo producen el mismo
resultado (FR-016).

## Lote (entrada de `/predict/lote`, `/campana/contactos` y `/drift`)

| Campo | Tipo | Regla |
|---|---|---|
| `clientes` | lista de `Cliente` | de 1 a 1.000 elementos; vacío o más de 1.000 se rechaza (FR-009). `/campana/contactos` acepta hasta 5.000 (D5) |

El orden de entrada se conserva en la salida. Un solo cliente inválido rechaza todo el lote e indica su
posición (índice base 0 y base 1 en el mensaje) y el campo.

## ResumenRiesgo (salida de `/predict/lote`, persistido en `ultimo_lote.json`)

| Campo | Tipo | Regla |
|---|---|---|
| `total_clientes` | entero | tamaño del lote |
| `clientes_riesgo_alto` | entero | probabilidad ≥ 0,70 |
| `porcentaje_riesgo_alto` | número | `clientes_riesgo_alto / total_clientes × 100` |
| `ingresos_mensuales_en_riesgo` | número (USD) | Σ `cargo_mensual` de los clientes en riesgo alto |
| `ingresos_6_meses_en_riesgo` | número (USD) | `ingresos_mensuales_en_riesgo × 6` |
| `version_modelo` | texto | versión usada |
| `fecha` | fecha-hora | marca de tiempo del cálculo |

Sin identificadores ni datos por cliente (FR-019). Lote sin riesgo alto: conteos e ingresos en cero. Solo se publica si el lote tiene al menos 20 clientes; con menos, se informa "lote demasiado pequeño para resumir" (FR-010).

## ListaContacto (salida de `/campana/contactos`)

| Campo | Tipo | Regla |
|---|---|---|
| `presupuesto` | número (USD) | 0,01 ≤ x ≤ 100.000; por defecto 2.000 (FR-012) |
| `costo_por_contacto` | número (USD) | 0,01 ≤ x ≤ 1.000; por defecto 8 (FR-012) |
| `max_contactos` | entero | `floor(presupuesto / costo_por_contacto)`; por defecto 250 |
| `contactos` | lista | clientes en riesgo alto con mayor ingreso esperado (probabilidad × `cargo_mensual`), hasta `min(max_contactos, clientes en riesgo alto)`; desempate por posición de entrada |
| `costo_total` | número (USD) | `len(contactos) × costo_por_contacto` |
| `aviso_uso_responsable` | texto | fijo (FR-005) |

Cada elemento de `contactos` lleva: `posicion_en_lote`, `probabilidad_churn`, `nivel_riesgo`,
`recomendacion` y `id_cliente` solo si el cliente lo envió. Si `presupuesto < costo_por_contacto`, la lista queda vacía con mensaje claro.

## CatalogoRecomendaciones (constante en `recomendaciones.py`)

| Nivel | Acción (provisional, `TODO(retencion)`) |
|---|---|
| alto | Contactar con oferta de retención; revisión humana antes de actuar |
| medio | Incluir en seguimiento; contactar solo si queda presupuesto |
| bajo | No actuar |

Una entrada por nivel. Cambiarlo exige aprobación de Retención y Legal. Ninguna entrada puede mencionar
negar servicio ni cambiar precios (prueba automática).

## InformeCambioDatos (salida de `POST /drift` y de `GET /drift`, que devuelve el último, persistido en `drift.json`)

| Campo | Tipo | Regla |
|---|---|---|
| `variables` | lista | una por cada una de las 7 variables de entrada |
| `variables[].nombre` | texto | columna de `config.FEATURES` |
| `variables[].psi` | número ≥ 0 | índice frente a la referencia de entrenamiento |
| `variables[].nivel` | `estable` / `alerta` / `critico` | < 0,10 / ≥ 0,10 / ≥ 0,25 |
| `estado_general` | `estable` / `alerta` / `critico` / `datos_insuficientes` | el peor de las variables; `datos_insuficientes` si el lote tiene menos de 100 filas |
| `recomendacion` | texto | "evaluar reentrenamiento" si alguna variable es crítica |
| `fecha` | fecha-hora | marca de tiempo |

## EstadoServicio (salida de `/health`)

| Campo | Tipo | Regla |
|---|---|---|
| `estado` | `sano` / `no_sano` | sano solo si el modelo está cargado e íntegro (huella correcta); describe la salud operativa |
| `modelo_cargado` | booleano | |
| `version_modelo` | texto o nulo | nulo si no hay modelo |
| `aprobado_para_despliegue` | booleano o nulo | compuerta técnica de la model card; nulo si no hay modelo |
| `alertas` | lista de texto | razones de no aprobación (FR-028); vacía si el modelo está aprobado |
| `error` | texto o nulo | "Modelo no disponible" si no está sano; nulo en otro caso (sin rutas ni trazas) |

Si el modelo no está disponible, las rutas de predicción responden con error de servicio no disponible y
no devuelven predicciones (FR-013).

## Modelo / ModelCard (archivo `models/model_card.json`)

Los nombres son los que escribe `train.py` (D7, I-10).

| Campo | Tipo | Regla |
|---|---|---|
| `version` | texto semántico | MAJOR.MINOR.PATCH; `config.MODEL_VERSION` |
| `algoritmo` | texto | `logreg` o `rf` |
| `fecha_entrenamiento` | fecha-hora | |
| `semilla` | entero | `config.SEED` |
| `hash_dataset` | texto | SHA-256 del CSV de entrenamiento |
| `hash_modelo` | texto | SHA-256 del archivo `churn_model.joblib`; solo en `model_card.json` (el `.joblib` contiene el card y no puede llevar su propio hash, I-8) (FR-021) |
| `features` | lista | solo `config.FEATURES`; nunca `rango_edad`, `id_cliente`, `periodo` ni `churn` |
| `umbral` | número | regla de FR-027 |
| `metricas_test` | objeto | recall, precision, ROC-AUC, F1, matriz de confusión y precision en el 5 % de mayor riesgo, sobre prueba |
| `metricas_negocio` | objeto | clientes e ingresos en riesgo, priorizados, costo y ROI estimado (I-6) |
| `equidad` | objeto | por `rango_edad`: tamaño, tasa de selección, recall y precision; diferencia máxima de recall; ratio de impacto dispar; reparto del 5 % de mayor riesgo frente al peso de cada grupo |
| `revision_proxies` | objeto | modelo con y sin `metodo_pago`, `tipo_plan` y `antiguedad_meses`: diferencia de recall por grupo (FR-024) |
| `criterios_cumplidos` | objeto | los 5 criterios de FR-018 más `equidad_recall`, `ratio_impacto_dispar` y `tamano_grupos`, cada uno verdadero o falso |
| `razones_no_aprobado` | lista de texto | vacía si todo se cumple; alimenta `alerta_equidad` y `alertas` |
| `aprobado_para_despliegue` | booleano | compuerta técnica: todos los criterios cumplidos |
| `aprobacion` | objeto | `aprobado_por`, `fecha` (vacío hasta que el dueño del modelo aprueba) |
| `perfil_referencia` | objeto | referencia de PSI (ver más abajo) |

Reglas: el modelo no se aprueba si algún criterio falla o si `aprobacion` está vacía (constitución VI). Un modelo no aprobado se sigue sirviendo con alerta (FR-026, D2).

## RegistroPrediccion (línea de `logs/predicciones.jsonl`)

| Campo | Tipo | Regla |
|---|---|---|
| `fecha` | fecha-hora | marca de tiempo |
| `id_codificado` | texto o nulo | SHA-256 de sal + identificador, 16 caracteres; nulo si no se envió identificador |
| `probabilidad_churn` | número 0–1 | |
| `nivel_riesgo` | `alto` / `medio` / `bajo` | |
| `version_modelo` | texto | |

No contiene los datos del cliente (FR-023). Se conserva 90 días (valor de partida) y solo lo lee Ciencia de Datos.

## Referencia de entrenamiento (campo `perfil_referencia` del model card)

Por variable: para las numéricas, los límites internos de los deciles (hasta 9; menos si hay valores repetidos) y las proporciones por intervalo;
para las categóricas, la proporción por categoría. Se calcula solo con el conjunto de entrenamiento del CSV al entrenar (D6, I-11).

## Relaciones

- `Lote` 1 → N `Cliente`; cada una produce una `Prediccion`.
- `Lote` 1 → 1 `ResumenRiesgo` (el último se persiste) y 0..1 `ListaContacto` por petición.
- `Lote` → 0..1 `InformeCambioDatos` frente a la `referencia de entrenamiento` del `Modelo` servido.
- `Prediccion` y `ListaContacto` dependen de un `Modelo` (versión) y del `CatalogoRecomendaciones`.
- Cada `Prediccion` genera una línea en el registro JSONL con el identificador codificado.
