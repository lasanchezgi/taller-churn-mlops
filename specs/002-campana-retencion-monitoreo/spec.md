# Feature Specification: Riesgo de churn, campaña de retención y monitoreo

**Feature Branch**: `002-campana-retencion-monitoreo`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Como analista de retención, quiero una API que reciba datos del cliente y devuelva probabilidad de churn, nivel de riesgo y recomendación de acción. Datos de entrada: antigüedad en meses, tipo de plan, cargo mensual, reclamos de los últimos 3 meses, uso de datos, método de pago y si renovó contrato. También necesito puntuar lotes mensuales, ver clientes e ingresos en riesgo y a quiénes contactar con un presupuesto de 2.000 USD (8 USD por contacto), saber si el servicio está sano y si los datos cambian frente al entrenamiento. Criterios: recall >= 0,70, precision >= 0,40, ROC-AUC >= 0,75. No uses la edad para predecir. No menciones tecnologías. Escribe en español."

## Clarifications

### Session 2026-11-06

- Q: ¿Qué significa exactamente "churn" y en qué plazo debe cancelarse el servicio para contarlo? → A: Churn = 1 si el cliente cancela el servicio en los 60 días siguientes al corte del periodo mensual; 0 en otro caso. La probabilidad devuelta es la de cancelar en esos 60 días.
- Q: ¿Qué tipo de número y qué límites máximos debe aceptar cada dato numérico del cliente? → A: Antigüedad: entero 1–120. Reclamos: entero 0–6. Cargo mensual: número de 10 a 1.000 USD. Uso de datos: número de 0 a 1.000 GB. Fuera de esos límites se rechaza con mensaje claro (topes de cargo y uso son valores de partida, ajustables por ciencia de datos).
- Q: ¿Quién define el texto de las recomendaciones de acción y qué tan fijo es? → A: El equipo de Retención define un catálogo corto y fijo, una recomendación por nivel de riesgo; Legal lo revisa. El sistema solo selecciona la entrada según el nivel y no crea texto propio.
- Q: ¿Se incluye una vista visual en esta funcionalidad, aunque antes estaba fuera de alcance? → A: Sí, de solo lectura, sin acciones sobre clientes (FR-019). Decisión tomada al planificar.
- Q: ¿Qué requisitos de seguridad, privacidad y equidad se añaden tras revisar el checklist `seguridad-privacidad-equidad`? → A: Se añaden FR-020 a FR-025, se precisan FR-002, FR-003, FR-005, FR-007, FR-010, FR-011, FR-012, FR-015, FR-018, FR-019, SC-005 y SC-010, y se confirma que esta especificación sustituye a la 001. Los valores numéricos nuevos (límite de 60 solicitudes por minuto, 90 días de retención, mínimo de 20 clientes por resumen, muestra de 100 predicciones, mínimo de 100 clientes por grupo, presupuesto máximo de 100.000 USD y costo máximo de 1.000 USD por contacto) son valores de partida que el dueño del modelo puede ajustar.
- Q: ¿Qué cambia tras la auditoría `docs/AUDITORIA.md`? → A: Decisiones D1–D8 de `docs/DECISIONES.md`: se exigen los 5 criterios de promoción de la constitución (FR-018, SC-004); un modelo que no pasa equidad se sigue sirviendo como no aprobado y con alerta de equidad en cada respuesta (FR-026, FR-028); el umbral nunca aborta el entrenamiento (FR-027); la lista de contacto se ordena por ingreso esperado y se calcula sobre el lote puntuado (FR-011); los datos de origen son la fuente de verdad del cambio de datos (FR-014, FR-016); la equidad añade el ratio de impacto dispar ≥ 0,80 (SC-010).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el riesgo de un cliente (Priority: P1)

Un analista de retención envía los datos de un cliente y recibe la probabilidad de que cancele, su nivel de riesgo, una acción recomendada y la versión del modelo que produjo el resultado.

**Why this priority**: es el núcleo del objetivo de negocio (priorizar la retención para bajar la tasa de cancelación de 25,5 % a ≤ 22,5 %). Sin esto no hay valor.

**Independent Test**: enviar un cliente válido y verificar que la respuesta trae probabilidad (0–1), nivel de riesgo, recomendación, versión del modelo y aviso de uso responsable.

**Acceptance Scenarios**:

1. **Given** un cliente con todos sus datos válidos, **When** se solicita su predicción, **Then** se devuelve la probabilidad de churn entre 0 y 1, el nivel de riesgo, la recomendación y la versión del modelo.
2. **Given** un cliente cuya probabilidad es ≥ 0,70, **When** se solicita su predicción, **Then** el nivel de riesgo es "alto".
3. **Given** un cliente cuya probabilidad es ≥ 0,50 y < 0,70, **When** se solicita su predicción, **Then** el nivel de riesgo es "medio"; si es < 0,50, es "bajo".
4. **Given** cualquier predicción, **When** se devuelve la respuesta, **Then** incluye el aviso de que el resultado apoya la decisión y requiere revisión humana.
5. **Given** un modelo servido que no está aprobado para despliegue, **When** se devuelve cualquier predicción, **Then** la respuesta incluye además una alerta de equidad con su razón.

---

### User Story 2 - Rechazar datos inválidos con mensajes claros (Priority: P1)

Cuando los datos del cliente están fuera de rango, incompletos, con categorías desconocidas o con campos no previstos (incluida la edad), el sistema rechaza la solicitud y explica qué campo falla y por qué.

**Why this priority**: la calidad de datos es un riesgo declarado; una predicción sobre datos inválidos es peor que no predecir.

**Independent Test**: enviar solicitudes con un valor fuera de rango, un campo faltante, una categoría inválida y un campo extra, y verificar el rechazo con mensaje claro en cada caso.

**Acceptance Scenarios**:

1. **Given** una antigüedad fuera de 1–120 meses, **When** se solicita la predicción, **Then** se rechaza con un error de validación que nombra el campo y el rango permitido.
2. **Given** una categoría fuera del dominio (p. ej. un plan inexistente), **When** se solicita la predicción, **Then** se rechaza con un error de validación que lista los valores permitidos.
3. **Given** una solicitud con un campo faltante o con un campo no previsto, **When** se solicita la predicción, **Then** se rechaza con un error de validación que indica el campo.
4. **Given** una solicitud que incluye la edad del cliente, **When** se solicita la predicción, **Then** se rechaza como campo no previsto y la edad nunca influye en la probabilidad.

---

### User Story 3 - Puntuar el lote mensual (Priority: P2)

Para la campaña mensual, el analista envía un lote de hasta 1.000 clientes y recibe una predicción por cliente, en el mismo orden, para poder priorizar la campaña.

**Why this priority**: es el modo de uso mensual de la campaña, pero depende de que la consulta individual funcione.

**Independent Test**: enviar un lote válido y verificar una respuesta por cliente; enviar un lote con un cliente inválido y verificar que el error indica cuál.

**Acceptance Scenarios**:

1. **Given** un lote de hasta 1.000 clientes válidos, **When** se solicita la predicción, **Then** se devuelve un resultado por cada cliente en el mismo orden.
2. **Given** un lote con más de 1.000 clientes o vacío, **When** se solicita la predicción, **Then** se rechaza con un mensaje claro del límite.
3. **Given** un lote con un cliente inválido, **When** se solicita la predicción, **Then** se rechaza el lote completo (para evitar resultados parciales que parezcan completos) e indica la posición del cliente y el campo que falla.

---

### User Story 4 - Ver clientes e ingresos en riesgo (Priority: P2)

Tras puntuar un lote, el analista ve cuántos clientes están en riesgo alto y cuántos ingresos mensuales representan, para dimensionar el problema y justificar la campaña.

**Why this priority**: conecta el modelo con el KPI de ingresos retenidos y con el contexto del negocio (≈ 27 % de los ingresos corresponden a clientes que se van).

**Independent Test**: puntuar un lote con riesgos conocidos y comprobar que el número de clientes en riesgo y la suma de sus cargos mensuales coinciden con el cálculo manual.

**Acceptance Scenarios**:

1. **Given** un lote puntuado, **When** se consulta el resumen de riesgo, **Then** se informa el total de clientes, el número en riesgo alto, su porcentaje y la suma de sus cargos mensuales (ingresos mensuales en riesgo).
2. **Given** un lote sin clientes de riesgo alto, **When** se consulta el resumen, **Then** el número en riesgo y los ingresos en riesgo son cero.

---

### User Story 5 - Elegir a quién contactar dentro del presupuesto (Priority: P2)

El analista indica el presupuesto del mes (2.000 USD por defecto) y el costo por contacto (8 USD por defecto) y recibe la lista de clientes a contactar, ordenada de mayor a menor ingreso esperado en riesgo (probabilidad de churn × cargo mensual), con el costo total.

**Why this priority**: es la decisión operativa de la campaña y el vínculo con el KPI de costo de campaña y ROI.

**Independent Test**: puntuar un lote con más de 250 clientes en riesgo alto y verificar que la lista tiene exactamente 250 clientes, ordenados por ingreso esperado descendente, con costo total de 2.000 USD.

**Acceptance Scenarios**:

1. **Given** un lote con más de 250 clientes en riesgo alto y los valores por defecto, **When** se solicita la lista de contacto, **Then** se devuelven los 250 clientes de mayor ingreso esperado en riesgo y un costo total de 2.000 USD.
2. **Given** un lote con menos clientes en riesgo alto que los contactos que permite el presupuesto, **When** se solicita la lista, **Then** se devuelven solo los clientes en riesgo alto y el costo real; si no hay ninguno, la lista queda vacía con un mensaje claro.
3. **Given** un presupuesto menor que el costo de un contacto, **When** se solicita la lista, **Then** la lista queda vacía con un mensaje claro.
4. **Given** clientes con el mismo ingreso esperado, **When** se arma la lista, **Then** el orden es estable (se respeta el orden de entrada).
5. **Given** la lista de contacto, **When** se entrega, **Then** incluye el aviso de que cada contacto requiere revisión humana antes de actuar.

---

### User Story 6 - Saber si el servicio está sano (Priority: P3)

El equipo de ciencia de datos puede comprobar que el servicio está activo, que el modelo está cargado y qué versión usa, y que el registro de actividad no expone identificadores de clientes.

**Why this priority**: soporta la operación y la privacidad, pero no entrega valor de negocio por sí solo.

**Independent Test**: consultar el estado del servicio y revisar el registro tras varias predicciones.

**Acceptance Scenarios**:

1. **Given** el servicio en marcha con el modelo cargado, **When** se consulta su estado, **Then** informa que está sano y la versión del modelo.
2. **Given** el modelo no disponible, **When** se consulta el estado, **Then** informa que no está sano y no se devuelven predicciones.
3. **Given** predicciones con identificador de cliente, **When** se revisa el registro, **Then** el identificador aparece solo en forma irreversible (codificada), nunca tal como lo escribió el cliente.
4. **Given** un modelo no aprobado para despliegue, **When** se consulta el estado, **Then** informa "sano" si está cargado e íntegro, indica que no está aprobado y lista la alerta con su razón.
5. **Given** un modelo cuya huella no coincide con la registrada en su ficha, **When** se consulta el estado, **Then** informa que no está sano y no se devuelven predicciones.

---

### User Story 7 - Detectar si los datos cambian frente al entrenamiento (Priority: P3)

El equipo de ciencia de datos compara un lote reciente con los datos de entrenamiento y ve, por variable, si la distribución cambió, con un nivel de estabilidad (estable, alerta o crítico).

**Why this priority**: protege la calidad del modelo en el tiempo (riesgo de cambio en los datos) y dispara el reentrenamiento.

**Independent Test**: comparar un lote igual al de entrenamiento (todo estable) y un lote con una variable desplazada de forma intencional (esa variable en crítico).

**Acceptance Scenarios**:

1. **Given** un lote con distribución similar a la de entrenamiento, **When** se consulta el cambio de datos, **Then** todas las variables salen "estable" (índice < 0,10).
2. **Given** una variable con índice entre 0,10 y 0,25, **When** se consulta, **Then** esa variable sale en "alerta".
3. **Given** una variable con índice ≥ 0,25, **When** se consulta, **Then** esa variable sale en "crítico" y el resultado recomienda evaluar el reentrenamiento.
4. **Given** un lote demasiado pequeño para comparar, **When** se consulta, **Then** se informa que no hay datos suficientes en lugar de un resultado engañoso.

---

### Edge Cases

- Valores en los límites (antigüedad 1 y 120, reclamos 0 y 6, cargo mensual 10 y 1.000 USD, uso de datos 0 y 1.000 GB): se aceptan.
- Valores justo fuera de los límites (antigüedad 0 o 121, reclamos 7, cargo mensual menor que 10 o mayor que 1.000 USD, uso de datos negativo o mayor que 1.000 GB) y números con decimales en antigüedad o reclamos: se rechazan con mensaje claro.
- Tipos incorrectos (texto en un campo numérico, valores nulos): se rechazan con mensaje claro.
- Probabilidad exactamente 0,70: nivel "alto".
- Presupuesto que no es múltiplo del costo por contacto: se contacta el máximo entero de clientes (p. ej. 2.010 USD → 251), sin superar nunca el número de clientes en riesgo alto del lote.
- Presupuesto o costo por contacto negativos o cero: se rechazan con mensaje claro.
- Modelo no disponible al arrancar o al consultar: el servicio informa el problema y no devuelve predicciones inventadas.
- Cliente de bajo riesgo: la recomendación indica no actuar, sin sugerir negar servicios ni cambiar precios.
- Lote con una sola categoría (todos del mismo plan): la comparación de cambio de datos sigue funcionando.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST aceptar los datos de un cliente (antigüedad en meses, tipo de plan, cargo mensual, reclamos en los últimos 3 meses, uso de datos, método de pago, renovación de contrato) y devolver la probabilidad de churn entre 0 y 1. "Churn" significa que el cliente cancela el servicio en los 60 días siguientes al corte del periodo mensual. *(KPI: tasa de cancelación)*
- **FR-002**: El sistema MUST devolver el nivel de riesgo, con tres niveles: "alto" cuando la probabilidad es ≥ 0,70, "medio" cuando es ≥ 0,50 y < 0,70, y "bajo" cuando es < 0,50. *(KPI: tasa de cancelación)*
- **FR-003**: El sistema MUST devolver una recomendación de acción tomada de un catálogo fijo definido por el equipo de Retención y revisado por Legal, con una entrada por nivel de riesgo; el sistema MUST NOT crear texto de recomendación propio ni sugerir negar servicios o cambiar precios. Ninguna entrada del catálogo puede contener términos como negar, suspender, cancelar el servicio, subir el precio, aumentar la tarifa o cobrar más; Legal puede ampliar esa lista. *(KPI: tasa de cancelación; uso responsable)*
- **FR-004**: El sistema MUST devolver la versión del modelo que generó cada predicción. *(Gobernanza)*
- **FR-005**: El sistema MUST incluir en cada respuesta de predicción y de lista de contacto el aviso de uso responsable (apoya la decisión; requiere revisión humana). La revisión humana consiste en que un analista de retención apruebe la lista antes de cualquier contacto, y su nombre y fecha quedan registrados en el proceso de campaña, fuera del servicio. *(Uso responsable)*
- **FR-006**: El sistema MUST validar cada entrada con rangos y dominios: antigüedad entera de 1 a 120 meses, reclamos enteros de 0 a 6, cargo mensual de 10 a 1.000 USD, uso de datos de 0 a 1.000 GB, y categorías cerradas para plan, método de pago y renovación. *(Calidad de datos)*
- **FR-007**: El sistema MUST rechazar campos faltantes, tipos incorrectos, valores fuera de dominio y campos no previstos con un error de validación y un mensaje claro. Un mensaje claro nombra el campo o parámetro, el motivo y los valores permitidos; esta definición se aplica a todos los rechazos, incluidos los límites de lote y de presupuesto. *(Calidad de datos)*
- **FR-008**: El sistema MUST NOT usar la edad del cliente para calcular la probabilidad; la edad solo se usa para auditar el modelo por grupo. *(Equidad)*
- **FR-009**: El sistema MUST permitir puntuar un lote de hasta 1.000 clientes, devolviendo un resultado por cliente en el mismo orden, y rechazar lotes mayores, vacíos o con algún cliente inválido indicando su posición. *(KPI: costo de campaña)*
- **FR-010**: El sistema MUST resumir un lote puntuado con el total de clientes, el número y porcentaje en riesgo alto y los ingresos mensuales en riesgo (suma de cargos mensuales de los clientes en riesgo alto), además de su equivalente a 6 meses. El resumen solo se publica si el lote tiene al menos 20 clientes; con menos, informa que el lote es demasiado pequeño para resumir. *(KPI: ingresos retenidos)*
- **FR-011**: El sistema MUST seleccionar a quiénes contactar: calcular el máximo de contactos como el entero de (presupuesto / costo por contacto), con valores por defecto de 2.000 USD y 8 USD (250 contactos), elegir entre los clientes del lote en riesgo alto (probabilidad ≥ 0,70), ordenados por ingreso esperado en riesgo (probabilidad de churn × cargo mensual) de mayor a menor con desempate estable, hasta el menor entre el máximo de contactos y el número de clientes en riesgo alto, y devolver la lista con el costo total. La selección se hace sobre el lote que se puntúa, de cualquier tamaño hasta el límite de la solicitud de contactos (5.000 clientes). La lista devuelve el identificador del cliente tal como lo envió el analista (solo en esa respuesta); el registro y la vista nunca lo muestran. *(KPI: costo de campaña, ROI)*
- **FR-012**: El sistema MUST aceptar presupuestos de 0,01 a 100.000 USD y costos por contacto de 0,01 a 1.000 USD, y rechazar los valores fuera de esos límites con un mensaje claro. *(KPI: costo de campaña)*
- **FR-013**: El sistema MUST informar si está sano (servicio activo y modelo cargado e íntegro, FR-021) y la versión del modelo; si el modelo no está disponible, MUST informarlo y NOT devolver predicciones. *(Operación)*
- **FR-014**: El sistema MUST comparar un lote reciente con la distribución de entrenamiento por cada variable de entrada y clasificar cada una como "estable" (índice < 0,10), "alerta" (≥ 0,10) o "crítico" (≥ 0,25), recomendando evaluar el reentrenamiento si hay alguna en crítico. La distribución de referencia es la del conjunto de entrenamiento de los datos de origen. El último informe calculado MUST poder consultarse sin enviar un lote. *(KPI: recall sostenido; riesgo de cambio en los datos)*
- **FR-015**: El sistema MUST registrar cada predicción sin exponer identificadores de cliente; solo una versión codificada: el mismo identificador da siempre el mismo código, dos identificadores distintos dan códigos distintos y no es posible recuperar el original a partir del código. El secreto usado para codificar MUST provenir de la configuración externa; si falta, el servicio MUST avisarlo al arrancar. *(Privacidad)*
- **FR-016**: El sistema MUST producir resultados reproducibles: la misma entrada con la misma versión del modelo da la misma probabilidad y la misma lista de contacto. Los datos de entrenamiento son el archivo de clientes del proyecto (fuente de verdad); el generador sintético solo sirve para demostraciones y pruebas. *(Reproducibilidad)*
- **FR-017**: El sistema MUST NOT tomar acciones sobre el cliente ni negar servicios o cambiar precios; solo informa y recomienda. *(Uso responsable)*
- **FR-018**: Para ser aprobado, el modelo MUST cumplir sobre el conjunto de prueba los 5 criterios de la constitución I: (1) recall de churn ≥ 0,70; (2) precision ≥ 0,40; (3) precision entre el 5 % de clientes de mayor probabilidad (k = 5 % del conjunto evaluado, equivalente a 250 de 5.000) ≥ 0,40; (4) ROC-AUC ≥ 0,75; (5) ROI estimado ≥ 3, calculado como (tasa de éxito de la campaña × suma de cargo mensual × 6 de los churners reales entre esos k clientes − k × costo por contacto) / (k × costo por contacto). El ROI incremental real se mide en producción con grupo de control. El modelo MUST publicar su recall y su precision por grupo de edad (18-25, 26-40, 41-60 y 60+) y el reparto del 5 % de clientes de mayor riesgo entre los grupos frente a su peso en la base, para auditar diferencias entre grupos. *(KPI: tasa de cancelación, costo de campaña, ROI; equidad)*
- **FR-019**: El sistema MUST ofrecer una vista visual de solo lectura con el estado del servicio, el último resumen de riesgo y el último informe de cambio de datos; si aún no hay lote puntuado, MUST mostrar un mensaje claro en lugar de cifras vacías. La vista MUST NOT mostrar identificadores ni datos personales de clientes: solo totales, porcentajes, ingresos agregados, estado, versión del modelo e índices por variable. Todo texto mostrado MUST tratarse como texto, nunca como contenido ejecutable. *(KPI: ingresos retenidos; riesgo de cambio en los datos)*
- **FR-020**: El sistema MUST limitar las solicitudes de cada origen a 60 por minuto (valor de partida) y responder con un mensaje claro cuando se supere. *(Seguridad)*
- **FR-021**: Al cargar el modelo, el sistema MUST comprobar que coincide con la huella registrada en su ficha; si no coincide, MUST NOT servirlo e informar que no está sano. *(Seguridad; gobernanza)*
- **FR-022**: Los mensajes de error MUST NOT incluir trazas internas, rutas de archivos ni el valor recibido del identificador de cliente. *(Seguridad; privacidad)*
- **FR-023**: El registro de predicciones MUST contener solo marca de tiempo, código del identificador, probabilidad, nivel de riesgo y versión del modelo, y MUST NOT contener los datos del cliente. Se conserva 90 días (valor de partida) y solo lo lee el equipo de ciencia de datos. *(Privacidad)*
- **FR-024**: En cada entrenamiento se MUST comparar el modelo con y sin cada variable que pueda sustituir a la edad (método de pago, tipo de plan y antigüedad) y registrar en la ficha del modelo la diferencia de recall por grupo de edad. *(Equidad)*
- **FR-025**: Cada trimestre, el equipo de ciencia de datos MUST cruzar las predicciones reales con el grupo de edad del sistema de origen (el servicio no recibe la edad) y reportar las diferencias entre grupos. *(Equidad)*
- **FR-026**: Mientras el modelo servido no esté aprobado para despliegue, cada respuesta de predicción individual y por lote MUST incluir una alerta de equidad que explique la razón (p. ej. brecha de recall entre grupos de edad), además del aviso de uso responsable. La edad nunca se usa para decidir ni para fijar umbrales por grupo. *(Equidad; uso responsable)*
- **FR-027**: Al entrenar, el umbral de decisión MUST elegirse así: el de mayor precision que alcance el recall mínimo; si ninguno lo alcanza, el de mayor recall. En ambos casos el entrenamiento NO se aborta: el modelo se guarda con el detalle de qué criterios cumple y queda como no aprobado si alguno falla. *(KPI: recall, precision; gobernanza)*
- **FR-028**: El estado del servicio MUST incluir si el modelo está aprobado para despliegue y una lista de alertas con sus razones, sin cambiar el significado de "sano" (que describe solo la salud operativa). *(Operación; gobernanza)*
- **FR-029** *(trazabilidad de experimentos, opcional; D11)*: Cuando se pida de forma explícita, cada entrenamiento MUST dejar una corrida comparable con: algoritmo, parámetros, semilla, umbral y regla de calibración; métricas técnicas, de negocio y de equidad; versión del modelo, huella del dataset, si queda aprobado y qué criterios cumple; la ficha del modelo, la matriz de confusión y el reporte de equidad; y un ejemplo de entrada que MUST NOT contener el identificador del cliente ni la edad. Si no se pide, el entrenamiento MUST funcionar igual y no crear ningún archivo de seguimiento. El servicio de predicción MUST NOT depender de este registro. *(Gobernanza; reproducibilidad)*
- **FR-030** *(registro de versiones de modelo, opcional; D11)*: Con el seguimiento activo, cada modelo entrenado MUST quedar registrado como versión «candidata». El estado «producción» MUST NOT asignarse durante el entrenamiento; solo un procedimiento aparte lo asigna, y únicamente si la ficha del modelo dice que está aprobado para despliegue. Se puede forzar solo con un motivo obligatorio, que queda registrado junto a la versión. *(Gobernanza; constitución VI)*
- **FR-031** *(trazabilidad del monitoreo, opcional; D11)*: Cuando se pida de forma explícita, cada simulación de cambio de datos MUST dejar una corrida con el índice de cambio de cada variable y el informe completo. *(Operación; gobernanza)*

### Key Entities *(include if feature involves data)*

- **Cliente**: persona con servicio de telecomunicaciones. Atributos de entrada: antigüedad en meses, tipo de plan, cargo mensual, reclamos en los últimos 3 meses, uso de datos, método de pago y renovación de contrato; opcionalmente un identificador de hasta 64 caracteres (letras, números, guion y guion bajo), opcional porque solo permite al analista reconocer su propia lista y no se usa para predecir; siempre se codifica de forma irreversible en el registro. La edad no es un atributo de entrada.
- **Catálogo de recomendaciones**: lista corta y fija, una acción por nivel de riesgo, definida por Retención y revisada por Legal; cambiarla requiere aprobación de ambos.
- **Predicción**: resultado para un cliente: probabilidad de cancelar en los 60 días siguientes al corte del periodo (churn), nivel de riesgo, recomendación, versión del modelo y aviso de uso responsable; mientras el modelo no esté aprobado, también la alerta de equidad.
- **Lote**: conjunto ordenado de hasta 1.000 clientes con una predicción por cada uno.
- **Resumen de riesgo**: totales de un lote puntuado: clientes en riesgo alto, porcentaje e ingresos mensuales en riesgo.
- **Lista de contacto**: clientes elegidos para la campaña del mes, ordenados por ingreso esperado en riesgo, con presupuesto, costo por contacto, número de contactos y costo total.
- **Informe de cambio de datos**: por variable, el índice de cambio frente al entrenamiento y su nivel (estable, alerta, crítico).
- **Corrida de seguimiento** *(opcional)*: registro de un entrenamiento o de una simulación de cambio de datos, con sus parámetros, métricas, etiquetas y archivos de evidencia.
- **Modelo**: versión del modelo de predicción, con sus métricas (globales y por grupo de edad), fecha, número de versión (por ejemplo 1.2.0), estado de aprobación y las razones por las que no está aprobado, si aplica.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las solicitudes con datos válidos recibe probabilidad, nivel de riesgo, recomendación y versión del modelo.
- **SC-002**: El 100 % de las solicitudes inválidas probadas (fuera de rango, categoría inválida, campo faltante, campo extra, edad incluida) se rechaza con un mensaje que nombra el campo afectado.
- **SC-003**: Un analista obtiene la predicción de un cliente en menos de 1 segundo y la de un lote de 1.000 clientes, con su resumen y lista de contacto, en menos de 10 segundos.
- **SC-004**: El modelo aprobado cumple los 5 criterios de FR-018 (recall ≥ 0,70; precision ≥ 0,40; precision en el 5 % de mayor riesgo ≥ 0,40; ROC-AUC ≥ 0,75; ROI estimado ≥ 3). Si alguno falla, el modelo se sigue sirviendo como no aprobado, con la razón explícita (FR-026, FR-028).
- **SC-005**: Cero identificadores de cliente en claro en el registro tras revisar una muestra de al menos 100 predicciones, sin ninguna coincidencia con un identificador original.
- **SC-006**: Incluir o cambiar la edad en una solicitud nunca altera la probabilidad: se rechaza o se ignora en el 100 % de los casos probados.
- **SC-007**: Con los valores por defecto, la lista de contacto tiene como máximo 250 clientes y un costo de hasta 2.000 USD, nunca más: con 250 o más clientes en riesgo alto tiene exactamente 250 y 2.000 USD; con menos, solo esos clientes.
- **SC-008**: El resumen de riesgo coincide con el cálculo manual (clientes e ingresos en riesgo) en el 100 % de los lotes de prueba.
- **SC-009**: El informe de cambio de datos clasifica correctamente como "estable" un lote igual al de entrenamiento y como "crítico" una variable desplazada de forma intencional en el 100 % de los casos probados. Un lote tomado del conjunto de prueba de los datos de origen sale "estable" en todas las variables (índice < 0,10) y el escenario de crisis (cargos y reclamos más altos) sale "crítico".
- **SC-010**: La diferencia de recall entre grupos de edad es ≤ 0,05 (igualdad de oportunidad, confirmado por el dueño del proyecto) y el ratio de impacto dispar (menor tasa de selección entre grupos / mayor) es ≥ 0,80 (regla de los cuatro quintos). Si alguna condición falla, o algún grupo tiene menos de 100 clientes en la prueba, el modelo no se aprueba: se sigue sirviendo con la alerta de FR-026 hasta que el dueño del modelo lo revise; la promoción es manual y queda documentada. Los criterios no se relajan para que el modelo pase.
- **SC-011**: Sin la capa opcional de seguimiento instalada, el entrenamiento, la API y las pruebas existentes (331 antes de D11) funcionan igual y no se crea ningún archivo de seguimiento; con ella, un entrenamiento y una simulación de cambio de datos dejan cada uno exactamente una corrida consultable (FR-029, FR-031).
- **SC-012**: Dos entrenamientos con algoritmos distintos se pueden comparar lado a lado por sus métricas técnicas, de negocio y de equidad; ningún entrenamiento deja una versión en producción, y el 100 % de las promociones forzadas registran su motivo (FR-030).

## Assumptions

- Los usuarios son analistas de retención y el equipo de ciencia de datos; no hay clientes finales con acceso directo.
- Esta especificación amplía y sustituye a `specs/001-api-churn` (confirmado por el dueño del proyecto el 2026-11-06). La 001 queda marcada como reemplazada y en caso de diferencia rigen las reglas de esta especificación.
- Las categorías válidas son las del ASUM-DM: plan (prepago, pospago_basico, pospago_premium), método de pago (tarjeta_credito, debito_automatico, efectivo, transferencia) y renovación (si, no).
- La lista de contacto se ordena por ingreso esperado en riesgo (probabilidad × cargo mensual). La precision en el 5 % de mayor riesgo del ASUM-DM mide la calidad del ranking del modelo por probabilidad; son dos usos distintos.
- Los ingresos en riesgo se calculan sobre el cargo mensual de los clientes en riesgo alto (probabilidad ≥ 0,70), con equivalente a 6 meses, igual que el valor del cliente retenido del ASUM-DM.
- Los umbrales de cambio de datos (alerta ≥ 0,10, crítico ≥ 0,25) son los del ASUM-DM.
- La distribución de entrenamiento de referencia se guarda al entrenar el modelo y sale solo del conjunto de entrenamiento de los datos de origen; el entrenamiento en sí es una funcionalidad separada.
- La autenticación de usuarios queda fuera del alcance de la versión inicial (taller con datos sintéticos). En el taller el servicio solo es accesible desde el equipo local; antes de producción MUST añadirse autenticación y control de acceso, incluidas las rutas de métricas y de vista.
- Datos personales: el identificador de cliente y cualquier dato que permita reconocer a una persona; los atributos de entrada, por sí solos, no lo son. Atributo sensible: hoy solo la edad; si se añade otro (género, ubicación), recibe el mismo tratamiento.
- Los derechos de acceso y supresión de datos y la base legal quedan fuera del taller (datos sintéticos) y son obligatorios antes de usar datos reales.
- Los topes de rangos y los valores de partida de esta especificación los revisa el equipo de ciencia de datos en la revisión trimestral.
- Abierto en el ASUM-DM y no resuelto aquí: la meta de −3 pp frente a lo que logran 250 contactos al mes (el ASUM-DM documenta la brecha; la decisión es del negocio).
- Se incluye una vista visual de solo lectura (FR-019); no permite acciones sobre clientes.
- Fuera de alcance: reentrenamiento automático, vistas visuales con acciones y cualquier acción automática sobre el cliente.
- Los datos son sintéticos; los resultados no se extrapolan a clientes reales sin revalidar.
