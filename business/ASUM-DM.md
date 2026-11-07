# ASUM-DM · Predicción de churn en telecomunicaciones

| Campo | Valor |
|---|---|
| Proyecto | Churn Telco: API de riesgo de cancelación y apoyo a la retención |
| Versión / fecha | 1.0 / 2026-11-06 |
| Patrocinador de negocio | Gerencia de Retención de Clientes (rol) |
| Dueño del modelo | Líder de Ciencia de Datos (rol) |
| Revisado por pares | ☐ Par 1: ______ ☐ Par 2: ______ (pendiente; paso humano de la salida a producción) |

## 1. Entendimiento del negocio
### 1.1 Objetivo de negocio
Reducir la tasa de cancelación mensual de 25,5 % a 22,5 % o menos (−3 pp) en 6 meses, mediante campañas de retención dirigidas a los clientes con mayor riesgo de irse.

### 1.2 KPIs de negocio
| KPI | Definición (fórmula) | Línea base | Meta |
|---|---|---|---|
| Tasa de cancelación | Clientes que cancelan en el mes / clientes activos al inicio del mes. Se mide contra un grupo de control (10 % sin contactar) y como promedio móvil de 3 meses | 25,5 % (1.275 de 5.000, periodo 2026-09) | ≤ 22,5 % a 6 meses |
| Ingresos retenidos (incrementales) | Σ (cargo_mensual × 6) de los clientes contactados que no cancelan − el mismo valor esperado en el grupo de control (retención natural) | Retención natural del grupo de control (sin campaña focalizada; se mide en el primer mes) | ≥ 8.000 USD/mes (4 × 2.000 USD de costo) |
| Costo de campaña de retención | Clientes contactados × 8 USD | 0 USD y 0 contactos dirigidos hoy (no hay priorización); si existe campaña masiva, usar su gasto real | ≤ 2.000 USD/mes (máx. 250 contactos) |
| ROI de campaña | (Ingresos retenidos incrementales − costo de campaña) / costo de campaña | 0 (sin campaña) | ≥ 3 (equivale a ingresos ≥ 4 veces el costo) |
| Costo por cliente retenido | Costo de campaña / clientes retenidos | Sin línea base (se mide en el primer mes) | ≤ 8 / (0,30 × precision@250) USD; ≈ 67 USD con precision 0,40 |

Nota: el churn del modelo se define a 60 días (§2) y la tasa de cancelación se reporta mensual; ambas deben calcularse sobre el mismo corte de periodo para ser comparables.

Contexto: los clientes que se van representan ≈ 67.209 USD/mes de ingresos (27 % de los 247.527 USD/mes totales).

### 1.3 Supuestos (presupuesto, costo por contacto, tasa de éxito de la campaña)
- Presupuesto mensual: 2.000 USD. Costo por contacto: 8 USD. Por tanto, se pueden contactar como máximo 250 clientes por mes.
- Tasa de éxito: 30 % de los clientes contactados que iban a irse se retienen.
- Valor de un cliente retenido: su cargo mensual × 6 meses (supuesto explícito, conservador).
  - Con valor a 1 mes la campaña no se paga: se necesitaría precision ≈ 0,51 (8 / (0,30 × 52,7)).
  - Con valor a 6 meses el punto de equilibrio es precision ≈ 0,08 (8 / (0,30 × 52,7 × 6)).
- Ejemplo con precision 0,40: 250 contactos → 100 churners → 30 retenidos × 52,7 USD × 6 ≈ 9.490 USD frente a 2.000 USD de costo (≈ 4,7 veces).
- Referencia del taller (README): ROC-AUC ≈ 0,81, recall ≈ 0,73, precision ≈ 0,49 (métricas globales del modelo con umbral 0,50, no del top 250). Con precision 0,49: ≈ 122 churners contactados → 37 retenidos → ≈ 11.600 USD.
- Tope de 250 contactos: con ≈ 1.275 churners al mes, contactar 250 clientes cubre como máximo ≈ 20 % de ellos (≈ 8 % con precision 0,40). Por eso se separan dos métricas (§6): recall global del modelo (calidad del ranking) y precision@250 (lo que realmente se contacta). Contactar a todos los que cumplen recall 0,70 exigiría ≈ 1.900 contactos (≈ 15.200 USD/mes), fuera del presupuesto.
- **Punto abierto (pendiente de decisión del patrocinador):** retener ≈ 30–37 clientes al mes baja la tasa mensual ≈ 0,6–0,7 pp sobre 5.000 clientes, no 3 pp. La meta de −3 pp (§1.1) requiere subir presupuesto/contactos, ampliar la base de la campaña o redefinir la meta (p. ej., acumulada). No se modifica hasta que se decida.
- Los datos son sintéticos; las cifras reales de la empresa deben reemplazar estos supuestos antes de producción.

### 1.4 Brecha de la meta de −3 pp (D10 · riesgo abierto del negocio)
La meta de −3 pp **no cambia** (decisión D10): es del negocio, no del equipo técnico. Esta sección solo mide la distancia.

Meta en cifras: 25,5 % → 22,5 % sobre 5.000 clientes son 1.275 → 1.125 cancelaciones al mes, es decir **150 retenidos al mes**.

Con el modelo actual (precision medida en el conjunto de prueba de 1.250 clientes, con k escalado a la base de 5.000, ordenados por
probabilidad), 30 % de éxito de la campaña y 8 USD por contacto:

| Contactos al mes | Precision de lo contactado | Clientes retenidos | Baja de la tasa | Costo |
|---|---|---|---|---|
| 250 (hoy, tope del presupuesto) | 0,758 | ≈ 57 | ≈ 1,1 pp | 2.000 USD |
| 500 | 0,680 | ≈ 102 | ≈ 2,0 pp | 4.000 USD |
| 750 | 0,636 | ≈ 143 | ≈ 2,9 pp | 6.000 USD |
| **≈ 800** | 0,640 | **≈ 154** | **≈ 3,1 pp** | **≈ 6.400 USD** |
| 1.000 | 0,604 | ≈ 181 | ≈ 3,6 pp | 8.000 USD |

Fórmula (se genera con `uv run python scripts/brecha_meta.py`):
`retenidos = contactos × precision@k × tasa_éxito` y `baja (pp) = 100 × retenidos / 5.000`, con tasa_éxito = 0,30 (supuesto fijo) y
precision@k medida en el conjunto de prueba con k = contactos × 1.250 / 5.000 (250 contactos → k = 62). Ejemplo: 250 × 0,758 × 0,30 = 56,9 → 1,14 pp.

Por qué la auditoría inicial decía 0,6–0,7 pp y ahora ≈ 1,1 pp: solo cambió la precision supuesta (éxito 30 % y base 5.000 son iguales).

| Supuesto de precision (250 contactos) | Precision | Retenidos | Baja |
|---|---|---|---|
| Mínima aceptada (`MIN_PRECISION`) | 0,40 | 30,0 | 0,60 pp |
| Global del modelo con su umbral (los 475 marcados) | 0,493 | 36,9 | 0,74 pp |
| Top 5 % por probabilidad (los 250 que realmente se contactan) | 0,758 | 56,9 | **1,14 pp** |

La cifra correcta para la campaña es la última: se contacta a los de mayor probabilidad, y su precision es mayor que la promedio de todos los marcados.
Las anteriores subestimaban porque usaban un piso (0,40) o el promedio global. Incertidumbre: con k = 62 el error estándar de la precision es ≈ 0,054, es decir ≈ ±0,16 pp.

Lectura:
- La campaña actual (250 contactos, 2.000 USD) mueve la tasa ≈ 1,1 pp (≈ 0,6 pp solo si la precision fuera la mínima aceptada). Ninguna llega a −3 pp;
  con 250 contactos haría falta una precision de 2,0, imposible.
- Para −3 pp hacen falta **≈ 800 contactos y ≈ 6.400 USD al mes** (3,07 pp): ≈ 3,2 veces el presupuesto vigente. Con valor de cliente a 6 meses y cargo medio de
  52,7 USD, el ROI bruto sería ≈ 6 (aún sin descontar la retención natural del grupo de control).
- Opciones del negocio (no se eligió ninguna): subir el presupuesto a ≈ 6.400 USD, ampliar la base de la campaña, o redefinir la meta (p. ej., acumulada
  en 12 meses o ≈ −1 pp mensual).
- Límites de la cifra: éxito fijo de 30 %, precision de la muestra de prueba (1.250 clientes) que baja al contactar más, datos sintéticos y sin grupo de
  control. Se recalcula con los datos del primer mes de campaña.

## 2. Traducción a problema de ML
| Elemento | Definición |
|---|---|
| Tipo de problema | Clasificación binaria supervisada (clase positiva = churn) |
| Variable objetivo (definición exacta y horizonte) | `churn` = 1 si el cliente cancela el servicio en los 60 días siguientes al corte del periodo; 0 en otro caso (horizonte acordado: 60 días) |
| Unidad de análisis | Cliente-periodo (un registro por cliente y mes) |
| Frecuencia de scoring | Mensual por lote (hasta 1.000 clientes por llamada) y consulta individual bajo demanda |
| Salida esperada | Probabilidad de churn, nivel de riesgo (alto si ≥ 0,70), recomendación de acción y versión del modelo |

## 3. Entendimiento de los datos
Fuente: `data/raw/churn_telco.csv`, 5.000 clientes, periodo 2026-09, sin nulos ni IDs duplicados.

| Variable | Tipo | Descripción | Hipótesis de negocio |
|---|---|---|---|
| antiguedad_meses | Numérica (1–120) | Meses como cliente | Los clientes nuevos se van más: ≤ 6 meses 45 % de churn; > 48 meses 4,5 % |
| tipo_plan | Categórica (prepago, pospago_basico, pospago_premium) | Plan contratado | Menor compromiso o precio alto aumenta la fuga: premium 32,2 %, prepago 26,8 %, pospago básico 20,8 % |
| cargo_mensual | Numérica (≥ 10 USD) | Facturación mensual | Cargos altos elevan el riesgo; media 49,5 USD (churners 52,7 USD) |
| reclamos_ult_3m | Numérica (0–6) | Reclamos en los últimos 3 meses | Más reclamos, más insatisfacción: 0 → 17,4 %; 3 o más → 51,1 % |
| uso_datos_gb | Numérica (≥ 0) | Consumo mensual de datos | Un uso bajo indica poco apego al servicio |
| metodo_pago | Categórica (tarjeta_credito, debito_automatico, efectivo, transferencia) | Forma de pago | El débito automático fideliza (22,1 %); el efectivo se asocia a más fuga (34,4 %) |
| renovo_contrato | Categórica (si, no) | Si renovó el contrato | No renovar es la señal más fuerte: 38,1 % frente a 13,3 % |
| rango_edad (sensible) | Categórica (18-25, 26-40, 41-60, 60+) | Grupo de edad del cliente | NO se usa para predecir; SÍ se usa para auditar sesgo por grupo (churn ≈ 25–26 % en todos los grupos) |

Reglas de calidad mínimas:
- Sin nulos en las variables del modelo; `id_cliente` único.
- Valores dentro de los dominios y rangos de arriba; categorías solo las definidas.
- La API rechaza campos no previstos y devuelve 422 con mensaje claro.
- Distribución del objetivo cercana a 25 % (control de desbalance).

## 4. Preparación de datos (pasos y controles)
1. Validar esquema, dominios y rangos; verificar nulos y duplicados.
2. Excluir de las features `id_cliente`, `periodo`, `churn` (objetivo) y `rango_edad` (sensible).
3. Separar entrenamiento y prueba 75/25, estratificado por `churn`, con semilla 42.
4. Numéricas: escalado estándar. Categóricas: codificación one-hot. Todo dentro de un `Pipeline` ajustado solo con entrenamiento (evita fuga de información).
5. Guardar el dataset procesado y registrar las distribuciones de entrenamiento como referencia para el drift.

## 5. Modelado (baseline y alternativa)
- **Baseline:** regresión logística (simple y explicable); se prueba primero.
- **Alternativa:** Random Forest, solo si el baseline no cumple los criterios de la sección 6.
- Se elige el modelo más simple que cumpla los umbrales. Semilla fija en todo lo aleatorio.
- Se guarda el modelo serializado con un model card (versión semántica, métricas, hash y fecha).
- Auditoría: métricas por `rango_edad` para detectar diferencias de recall o precision entre grupos.

## 6. Evaluación · Criterios de éxito
| Criterio (fórmula) | Línea base | Umbral mínimo | Justificación de negocio |
|---|---|---|---|
| Recall global clase churn = TP / (TP + FN), sobre el conjunto de prueba (25 %) | 0,255 (azar; prevalencia) o la regresión logística | ≥ 0,70 | Un falso negativo es un cliente que se va sin intervención: ≈ 52,7 USD/mes de ingreso perdido. Mide la calidad del modelo, no el volumen de contactos |
| Precision global clase churn = TP / (TP + FP), sobre el conjunto de prueba | 0,255 (azar; prevalencia) | ≥ 0,40 | Un falso positivo gasta 8 USD y molesta a un cliente que no se iba; con 0,40 el ROI sigue siendo positivo |
| Precision@250 = churners reales entre los 250 clientes de mayor riesgo / 250 | 0,255 (contactar al azar) | ≥ 0,40 | Es la precision de lo que realmente se contacta cada mes con el presupuesto de 2.000 USD |
| ROC-AUC | 0,50 (azar) | ≥ 0,75 (referencia del taller ≈ 0,81) | Garantiza que el modelo ordena el riesgo mejor que el azar y permite priorizar |
| ROI de campaña = (ingresos retenidos incrementales − costo) / costo, valor del cliente a 6 meses | 0 (sin campaña) | ≥ 3 (ingresos ≥ 4 veces los 2.000 USD de presupuesto) | Misma meta que §1.2: una sola definición de éxito de negocio |
| Diferencia máxima de recall entre grupos de `rango_edad` | 0,147 con el primer modelo (18-25: 0,797; 60+: 0,650) | ≤ 0,05 (confirmado, D3) | Detecta trato desigual por edad sin usarla como feature |
| Ratio de impacto dispar (menor tasa de selección / mayor) | 0,903 con el primer modelo | ≥ 0,80 (regla de los cuatro quintos, D3) | Detecta selección desigual por edad |
| Umbral de decisión | Calibrado en validación; por defecto 0,50 | Se elige el que cumpla recall global ≥ 0,70 y precision ≥ 0,40 | La campaña mensual contacta solo el top 250 por probabilidad, sin superar el tope de contactos |

## 7. Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|---|---|---|
| Sesgo | Trato desigual por edad u otros proxies | Edad excluida del modelo; auditoría de métricas por grupo; revisar proxies (p. ej., método de pago); alerta de equidad mientras el modelo no esté aprobado (D2); auditoría trimestral con la edad del sistema de origen (`docs/AUDITORIA_EQUIDAD.md`) |
| Calidad de datos | Predicciones erróneas por valores fuera de rango o faltantes | Validación con Pydantic (422), reglas de calidad, rechazo de campos extra |
| Drift | El modelo pierde precisión si cambian los clientes o el mercado | PSI por variable: alerta ≥ 0,10, crítico ≥ 0,25; monitoreo en `/metrics`; reentrenamiento |
| Meta de −3 pp fuera de alcance (D10) | La campaña vigente baja la tasa ≈ 1,1 pp, no 3 pp | Decisión del negocio sobre presupuesto, base o meta (§1.4); no la resuelve el equipo técnico |
| Uso indebido | Negar servicios, subir precios o decidir sin revisión humana | Aviso en cada respuesta, política de uso, aprobación humana de toda acción sobre el cliente |
| Privacidad | Exposición de identificadores de clientes | IDs con hash en los logs; sin datos personales en reportes; datos sintéticos en el taller |

## 8. Plan de despliegue
| Aspecto | Decisión |
|---|---|
| Modalidad (batch / tiempo real) | Batch mensual para la campaña, más API de consulta individual (`/predict`, `/predict/lote`) |
| Responsables (RACI) | R: Ciencia de Datos (modelo y monitoreo). A: Dueño del modelo. C: Retención (acciones) y Gobernanza/Legal. I: Patrocinador de negocio |
| Monitoreo | `/health`, `/metrics` (operación, negocio, drift), logs JSONL, dashboard en `/dashboard` |
| Frecuencia y disparadores de reentrenamiento | Revisión trimestral; reentrenar si PSI ≥ 0,25, si recall cae por debajo de 0,70, o si cambian datos o features (nueva versión del modelo) |
| Criterio de salida a producción | Métricas ≥ umbrales (incluida la equidad), `pytest` en verde, model card con versión y hash, ASUM-DM revisado por pares y aprobación del dueño del modelo |
| Modelo que no pasa la equidad (D2) | Se sigue sirviendo **como no aprobado**: `aprobado_para_despliegue = false` con sus razones en el model card, `alertas` en `/health` (sin cambiar `estado`) y `alerta_equidad` en cada respuesta de `/predict` y `/predict/lote`. La promoción es manual (dueño del modelo, `docs/GOBERNANZA.md`); ningún criterio se relaja y la edad no se usa para predecir ni para fijar umbrales por grupo. Hoy es el caso: brecha de recall 0,147 |

## 9. Uso responsable
- El modelo **apoya** la decisión de retención; no decide. Toda acción que afecte al cliente requiere revisión humana (analista de retención).
- No debe usarse para negar servicios, cambiar precios ni tomar decisiones automatizadas.
- No usa la edad para predecir; el sesgo se audita por grupo.
- Los logs guardan los identificadores con hash.
- Los datos del taller son sintéticos: no extrapolar resultados a clientes reales sin revalidar.
