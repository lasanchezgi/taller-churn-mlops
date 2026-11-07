# Churn Telco Constitution

Fuente de verdad, en orden de precedencia: `business/ASUM-DM.md`, esta constitución y
`specs/002-campana-retencion-monitoreo/{spec,plan,tasks}.md` (que reemplaza a `specs/001-api-churn`). Las reglas operativas del agente están en `AGENTS.md`.

## Core Principles

### I. Trazabilidad a los KPI del negocio
Todo requisito MUST trazarse a un KPI, objetivo o criterio de éxito de `business/ASUM-DM.md`
(reducir la cancelación de 25,5 % a ≤ 22,5 %; presupuesto de 2.000 USD/mes; máx. 250 contactos;
ROI ≥ 3). Cada requisito (`FR-xxx`) MUST nombrar el KPI al que sirve; un requisito sin KPI MUST
eliminarse o justificarse con una enmienda al ASUM-DM. Un modelo solo se promueve si cumple los
umbrales: recall global de churn ≥ 0,70, precision global ≥ 0,40, precision@250 ≥ 0,40,
ROC-AUC ≥ 0,75 y ROI ≥ 3.
Razón: el valor del proyecto es el retorno de la campaña, no la métrica en sí.

### II. Pruebas automáticas y pytest en verde (NON-NEGOTIABLE)
Cada requisito MUST tener al menos una prueba automática en `tests/` que lo verifique, y `pytest`
MUST pasar antes de integrar cualquier cambio. Todo cambio de lógica MUST venir con su prueba. Las
validaciones (422), la exclusión de `rango_edad`, el hash en logs, la semilla fija y la versión del
model card MUST tener pruebas explícitas.
Razón: son las garantías de seguridad y equidad del sistema; sin pruebas no son verificables.

### III. Reproducibilidad y autonomía de servicios
Todo proceso aleatorio (separación train/test 75/25 estratificada, entrenamiento, muestreo) MUST
usar la semilla fija `config.SEED` (42). El preprocesamiento MUST vivir dentro de un `Pipeline`
ajustado solo con datos de entrenamiento. El proyecto MUST ejecutarse completo sin servicios que
requieran cuentas, pagos, Kubernetes ni MLflow; las dependencias nuevas MUST ser locales y de
código abierto.
Razón: resultados repetibles y auditables por cualquier persona, sin fuga de información ni
dependencia de terceros.

### IV. Seguridad y privacidad (NON-NEGOTIABLE)
Toda entrada de la API MUST validarse con modelos Pydantic que impongan rangos y dominios
(p. ej. `antiguedad_meses` 1–120, `reclamos_ult_3m` 0–6, categorías cerradas). Los campos no
previstos MUST rechazarse, y los errores MUST devolver HTTP 422 con un mensaje claro. Las columnas
usadas MUST ser únicamente las definidas en `src/churn/config.py`. Los logs (formato JSONL) MUST
NOT contener identificadores de cliente en claro; MUST registrar un hash del identificador. Los
reportes y el dashboard MUST NOT incluir datos personales.
Razón: mitigar los riesgos de calidad de datos y de privacidad del ASUM-DM (sección 7).

### V. Explicabilidad y equidad (NON-NEGOTIABLE)
Se elige el modelo más simple que cumpla los umbrales (regresión logística primero; Random Forest
solo si el baseline no cumple). Los atributos sensibles MUST NOT usarse como predictores:
`rango_edad` solo se usa para auditar recall y precision por grupo, y se excluyen de las features
`id_cliente`, `periodo` y `churn`. Cada entrenamiento MUST incluir la auditoría por `rango_edad` y
la revisión de proxies potenciales (p. ej. `metodo_pago`), y sus resultados MUST quedar en el
model card.
Razón: evitar trato desigual por edad y poder explicar cada predicción al analista de retención.

### VI. Gobernanza y versionado
Cada modelo guardado MUST acompañarse de un model card con versión semántica (MAJOR.MINOR.PATCH),
métricas, hash y fecha. Un cambio de datos o de features MUST generar una nueva versión del
modelo. Nada pasa a producción sin: métricas ≥ umbrales, `pytest` en verde, model card completo,
ASUM-DM revisado por pares y aprobación explícita del dueño del modelo.
Razón: trazabilidad de qué modelo tomó qué decisión y control de cambios antes de afectar a
clientes.

### VII. Supervisión humana
El sistema apoya la decisión de retención; MUST NOT decidir. Toda acción que afecte al cliente
MUST contar con revisión humana de un analista de retención. El modelo MUST NOT usarse para negar
servicios, cambiar precios ni tomar decisiones automatizadas, y cada respuesta de la API MUST
incluir el aviso de uso responsable.
Razón: uso responsable del ASUM-DM (sección 9) y mitigación del riesgo de uso indebido.

## Restricciones técnicas y de alcance

- Stack: Python, scikit-learn, FastAPI, Pydantic, pytest; entorno gestionado con `uv`.
- Monitoreo con `/health`, `/metrics` y `/dashboard`; drift por PSI (alerta ≥ 0,10, crítico ≥ 0,25).
- Los datos del taller son sintéticos; no se extrapolan resultados a clientes reales sin
  revalidar.

## Flujo de desarrollo y calidad

- Antes de escribir código se cita la tarea (`T0xx`) y el requisito (`FR-xxx`) que se implementa.
- Los cambios son pequeños: un archivo o una función por paso.
- Código, comentarios y documentación en español, con comentarios breves.
- Reentrenamiento: revisión trimestral, o si PSI ≥ 0,25, o si el recall cae por debajo de 0,70.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del repositorio. Si una instrucción
contradice la especificación o esta constitución, se detiene el trabajo y se consulta.
Las enmiendas MUST documentarse en un cambio con su justificación, ser aprobadas por el dueño del
modelo y actualizar la versión: MAJOR (eliminar o redefinir principios de forma incompatible),
MINOR (añadir principios o ampliar guía de forma material), PATCH (aclaraciones y redacción).
Toda revisión de código y de PR MUST verificar el cumplimiento de estos principios; la
complejidad adicional MUST justificarse. La guía operativa en ejecución está en `AGENTS.md`.

**Version**: 2.0.1 | **Ratified**: 2026-11-06 | **Last Amended**: 2026-11-06
