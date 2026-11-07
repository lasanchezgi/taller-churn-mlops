# Feature Specification: Servicio de predicción de riesgo de cancelación

**Feature Branch**: `001-api-churn`

**Created**: 2026-11-06

**Status**: Reemplazada por `specs/002-campana-retencion-monitoreo` (2026-11-06)

**Input**: User description: "Servicio de predicción de riesgo de cancelación: recibe los datos de un cliente, verifica que sean válidos y devuelve la probabilidad de cancelación, el nivel de riesgo, la recomendación y la versión del modelo"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el riesgo de un cliente (Priority: P1)

Un analista de retención envía los datos de un cliente y recibe la probabilidad de que cancele, su nivel de riesgo, una acción recomendada y la versión del modelo que produjo el resultado.

**Why this priority**: es el núcleo del objetivo de negocio (priorizar campañas de retención para bajar la cancelación de 25,5 % a ≤ 22,5 %). Sin esto no hay valor.

**Independent Test**: enviar un cliente válido y verificar que la respuesta trae probabilidad (0–1), nivel de riesgo, recomendación y versión del modelo.

**Acceptance Scenarios**:

1. **Given** un cliente con todos sus datos válidos, **When** se solicita su predicción, **Then** se devuelve la probabilidad de churn entre 0 y 1, el nivel de riesgo, la recomendación y la versión del modelo.
2. **Given** un cliente cuya probabilidad es ≥ 0,70, **When** se solicita su predicción, **Then** el nivel de riesgo es "alto".
3. **Given** un cliente cuya probabilidad es < 0,70, **When** se solicita su predicción, **Then** el nivel de riesgo no es "alto".
4. **Given** cualquier predicción, **When** se devuelve la respuesta, **Then** incluye el aviso de que el resultado apoya la decisión y requiere revisión humana.

---

### User Story 2 - Rechazar datos inválidos con mensajes claros (Priority: P1)

Cuando los datos del cliente están fuera de rango, incompletos, con categorías desconocidas o con campos no previstos, el sistema rechaza la solicitud y explica qué campo falla y por qué.

**Why this priority**: la calidad de datos es un riesgo declarado; una predicción sobre datos inválidos es peor que no predecir.

**Independent Test**: enviar solicitudes con un valor fuera de rango, un campo faltante, una categoría inválida y un campo extra, y verificar el rechazo con mensaje claro en cada caso.

**Acceptance Scenarios**:

1. **Given** una antigüedad fuera de 1–120 meses, **When** se solicita la predicción, **Then** se rechaza con un mensaje de error que nombra el campo y el rango permitido.
2. **Given** una categoría fuera del dominio (p. ej. plan inexistente), **When** se solicita la predicción, **Then** se rechaza con un mensaje de error que lista los valores permitidos.
3. **Given** una solicitud con un campo faltante o con un campo no previsto, **When** se solicita la predicción, **Then** se rechaza con un mensaje de error que indica el campo.
4. **Given** una solicitud con `rango_edad`, **When** se solicita la predicción, **Then** el dato no influye en la probabilidad calculada.

---

### User Story 3 - Consultar varios clientes a la vez (Priority: P2)

Para la campaña mensual, el analista envía un lote de hasta 1.000 clientes y recibe una predicción por cliente, de modo que pueda priorizar los hasta 250 contactos del mes.

**Why this priority**: es el modo de uso mensual de la campaña, pero depende de que la consulta individual funcione.

**Independent Test**: enviar un lote válido y verificar una respuesta por cliente; enviar un lote con un cliente inválido y verificar que el error indica cuál.

**Acceptance Scenarios**:

1. **Given** un lote de hasta 1.000 clientes válidos, **When** se solicita la predicción, **Then** se devuelve un resultado por cada cliente en el mismo orden.
2. **Given** un lote con más de 1.000 clientes, **When** se solicita la predicción, **Then** se rechaza con un mensaje claro del límite.
3. **Given** un lote con un cliente inválido, **When** se solicita la predicción, **Then** se rechaza e indica la posición del cliente y el campo que falla.

---

### User Story 4 - Verificar el estado del servicio y su trazabilidad (Priority: P3)

El equipo de ciencia de datos puede comprobar que el servicio está activo y qué versión del modelo usa, y los registros de actividad no exponen identificadores de clientes.

**Why this priority**: soporta operación y privacidad, pero no entrega valor de negocio por sí solo.

**Independent Test**: consultar el estado del servicio y revisar los registros tras varias predicciones.

**Acceptance Scenarios**:

1. **Given** el servicio en marcha, **When** se consulta su estado, **Then** informa que está activo y la versión del modelo cargado.
2. **Given** predicciones con identificador de cliente, **When** se revisan los registros, **Then** el identificador aparece solo en forma irreversible (codificada), nunca tal como lo escribió el cliente.

---

### Edge Cases

- Valores en los límites (antigüedad 1 y 120, reclamos 0 y 6, cargo mensual exactamente 10 USD): se aceptan.
- Tipos incorrectos (texto en un campo numérico, valores nulos): se rechazan con mensaje claro.
- Probabilidad exactamente 0,70: nivel "alto".
- Lote vacío: se rechaza con mensaje claro.
- Modelo no disponible al arrancar o al consultar: el servicio informa el problema y no devuelve predicciones inventadas.
- Cliente de bajo riesgo: la recomendación indica no actuar, sin sugerir negar servicios ni cambiar precios.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST aceptar los datos de un cliente (antigüedad en meses, tipo de plan, cargo mensual, reclamos en los últimos 3 meses, uso de datos, método de pago, renovación de contrato) y devolver la probabilidad de churn entre 0 y 1.
- **FR-002**: El sistema MUST devolver el nivel de riesgo, siendo "alto" cuando la probabilidad es ≥ 0,70.
- **FR-003**: El sistema MUST devolver una recomendación de acción coherente con el nivel de riesgo.
- **FR-004**: El sistema MUST devolver la versión del modelo que generó cada predicción.
- **FR-005**: El sistema MUST incluir en cada respuesta el aviso de uso responsable (apoya la decisión; requiere revisión humana).
- **FR-006**: El sistema MUST validar cada entrada con rangos y dominios: antigüedad 1–120, reclamos 0–6, cargo mensual ≥ 10 USD, uso de datos ≥ 0, y categorías cerradas para plan, método de pago y renovación.
- **FR-007**: El sistema MUST rechazar campos faltantes, tipos incorrectos, valores fuera de dominio y campos no previstos con un mensaje de error que nombre el campo.
- **FR-008**: El sistema MUST NOT usar `rango_edad` para calcular la probabilidad.
- **FR-009**: El sistema MUST permitir consultar un lote de hasta 1.000 clientes, devolviendo un resultado por cliente, y rechazar lotes mayores o vacíos.
- **FR-010**: El sistema MUST informar su estado (activo) y la versión del modelo cargado.
- **FR-011**: El sistema MUST registrar cada predicción sin exponer identificadores de cliente; solo una versión codificada que no permite reconocer al cliente.
- **FR-012**: El sistema MUST producir resultados reproducibles: la misma entrada con la misma versión del modelo da la misma probabilidad.
- **FR-013**: El sistema MUST NOT tomar acciones sobre el cliente ni negar servicios o cambiar precios; solo informa.

### Key Entities *(include if feature involves data)*

- **Cliente**: persona con servicio de telecomunicaciones. Atributos de entrada: antigüedad en meses, tipo de plan, cargo mensual, reclamos en los últimos 3 meses, uso de datos, método de pago y renovación de contrato; opcionalmente un identificador (solo para trazabilidad, siempre codificado de forma irreversible en los registros).
- **Predicción**: resultado para un cliente: probabilidad de churn, nivel de riesgo, recomendación, versión del modelo y aviso de uso responsable.
- **Lote**: conjunto ordenado de hasta 1.000 clientes con una predicción por cada uno.
- **Modelo**: versión del modelo de predicción, con sus métricas y fecha, identificada por un número de versión (por ejemplo 1.2.0).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las solicitudes con datos válidos recibe probabilidad, nivel de riesgo, recomendación y versión del modelo.
- **SC-002**: El 100 % de las solicitudes inválidas probadas (fuera de rango, categoría inválida, campo faltante, campo extra) se rechaza con un mensaje que nombra el campo afectado.
- **SC-003**: Un analista obtiene la predicción de un cliente en menos de 1 segundo y la de un lote de 1.000 clientes en menos de 10 segundos.
- **SC-004**: El modelo servido cumple los umbrales de negocio: recall de churn ≥ 0,70, precision ≥ 0,40 y ROC-AUC ≥ 0,75.
- **SC-005**: Cero identificadores de cliente en claro en los registros tras una revisión de una muestra de predicciones.
- **SC-006**: Cambiar el valor de `rango_edad` no altera la probabilidad en el 100 % de los casos probados.
- **SC-007**: El resultado del lote mensual permite seleccionar hasta 250 clientes de mayor riesgo para la campaña dentro del presupuesto de 2.000 USD.

## Assumptions

- Los usuarios son analistas de retención y el equipo de ciencia de datos; no hay clientes finales con acceso directo.
- Las categorías válidas son las del ASUM-DM: plan (prepago, pospago_basico, pospago_premium), método de pago (tarjeta_credito, debito_automatico, efectivo, transferencia) y renovación (si, no).
- El modelo ya está entrenado y disponible; la construcción del modelo y el seguimiento de cambios en los datos son funcionalidades separadas.
- La autenticación de usuarios queda fuera del alcance de la versión inicial (taller con datos sintéticos).
- El umbral de riesgo alto es 0,70, tomado del ASUM-DM; la recomendación se deriva del nivel de riesgo.
- Fuera de alcance: panel visual, métricas operativas, reentrenamiento y cualquier acción automática sobre el cliente.
- Los datos son sintéticos; los resultados no se extrapolan a clientes reales sin revalidar.
