# Gobernanza del modelo de churn

Reglas para aprobar, versionar, vigilar y retirar el modelo. Se basan en `business/ASUM-DM.md` (§8),
la constitución (principios VI y VII) y la spec `specs/002-campana-retencion-monitoreo/`.

> **Estado de este documento:** las reglas son vigentes. Los pasos que dependen de código aún no
> construido están marcados con **(pendiente)** y su tarea. Los nombres de las personas que ocupan
> cada rol no se definen aquí: los asigna el patrocinador.

## 1. Quién aprueba un modelo (RACI)

| Actividad | Ciencia de Datos | Dueño del modelo | Retención | Gobernanza/Legal | Patrocinador |
|---|:-:|:-:|:-:|:-:|:-:|
| Entrenar y evaluar el modelo | **R** | A | I | I | I |
| Revisar los criterios técnicos (recall, precision, ROC-AUC, equidad) | **R** | A | C | C | I |
| Textos de recomendación al analista | C | A | **R** | C (revisa que no niegue servicio ni cambie precios) | I |
| **Aprobar la salida a producción** | C | **A/R** | C | C | I |
| Monitorear drift y métricas | **R** | A | I | I | I |
| Decidir reentrenar | **R** | A | C | I | I |
| Retirar o revertir una versión | **R** | **A** | I | I | I |
| Acciones sobre clientes | I | I | **R** (revisión humana) | C | A |

R = ejecuta · A = responde por el resultado y firma · C = se consulta · I = se informa.

Reglas:
- Solo el **dueño del modelo** aprueba. La aprobación es humana y explícita: `aprobado_para_despliegue`
  en el model card es solo la **compuerta técnica**; no sustituye la firma (constitución VI).
- La aprobación se registra en el campo `aprobacion` del model card (`aprobado_por` y `fecha`).
  Mientras sean `null`, el modelo **no está aprobado**.
- Quien entrena no aprueba su propio modelo.
- **Un modelo no aprobado se sigue sirviendo (D2)**, porque el servicio es una herramienta de apoyo con revisión
  humana. Mientras `aprobado_para_despliegue` sea `false`: `/health` mantiene `estado` = `sano` (salud
  operativa) y agrega `aprobado_para_despliegue=false` y `alertas` con las razones; cada respuesta de `/predict`
  y `/predict/lote` trae `alerta_equidad` además del aviso de revisión humana. La promoción es **manual**:
  el dueño del modelo la registra en `aprobacion` después de revisar las razones; ningún criterio se relaja
  para que el modelo «pase».

## 2. Condiciones para pasar a producción

Todas deben cumplirse (ASUM-DM §8, constitución VI):

| # | Condición | Cómo se comprueba |
|---|---|---|
| 1 | Los 5 criterios de la constitución I en el conjunto de prueba: recall ≥ 0,70, precision ≥ 0,40, precision en el 5 % de mayor riesgo ≥ 0,40, ROC-AUC ≥ 0,75 y ROI estimado ≥ 3 | `recall`, `precision`, `precision_top`, `roc_auc` y `roi` en `criterios_cumplidos` |
| 2 | Equidad (D3): diferencia de recall entre grupos de edad ≤ 0,05, ratio de impacto dispar ≥ 0,80 y grupos de al menos 100 clientes | `equidad_recall`, `ratio_impacto_dispar` y `tamano_grupos`; las razones quedan en `razones_no_aprobado` |
| 3 | `uv run pytest` en verde | salida guardada como evidencia (sección 3) |
| 4 | Model card completo: versión, métricas, huella (hash) y fecha | `models/model_card.json` |
| 5 | ASUM-DM revisado por pares | acta o comentario de revisión |
| 6 | Aprobación del dueño del modelo | campo `aprobacion` |

Si falla cualquiera, la versión no se despliega y se documenta el motivo.

## 3. Evidencias que se guardan

| Evidencia | Archivo | Lo genera | Qué prueba |
|---|---|---|---|
| Model card | `models/model_card.json` (copia dentro de `models/churn_model.joblib`) | `python -m churn.train` | versión, semilla, huella del dataset, umbral, métricas, equidad, perfil de referencia, aprobación |
| Evaluación | `reports/metrics/evaluacion.json` | `python -m churn.train` | métricas técnicas, de negocio y de equidad en test |
| Mitigación de equidad | `reports/metrics/mitigacion_equidad.json` | `python -m churn.mitigacion` | un intento: regresión logística frente a Random Forest, modelo sin cada variable que podría sustituir a la edad y asociación de cada variable con la edad |
| Cambio de datos | `reports/metrics/drift.json` | `python -m churn.drift` | PSI por variable y, en simulación, comparación base vs. crisis |
| Pruebas | `reports/pruebas/pytest-<versión>.txt` | `uv run pytest -v` redirigido a archivo (manual) | que las reglas del sistema se cumplen |
| Especificación | `specs/002-campana-retencion-monitoreo/spec.md`, `plan.md`, `tasks.md` | Spec Kit | qué se pidió, cómo se diseñó y qué tareas están cerradas |
| Registro de predicciones | `logs/predicciones.jsonl` | la API (pendiente, T047) | auditoría sin identificadores en claro |

Cómo guardar el resultado de las pruebas:

```bash
mkdir -p reports/pruebas
uv run pytest -v > reports/pruebas/pytest-1.0.0.txt
```

Reglas de custodia:
- Las evidencias de una versión se conservan mientras esa versión pueda ser restaurada.
- `models/`, `reports/` y `logs/` son generados; hoy `.gitignore` solo excluye `logs/*.jsonl`
  (decidir si se versionan en T102).
- El registro de predicciones se conserva 90 días (valor de partida, FR-023) y solo lo lee Ciencia de Datos.
- Ninguna evidencia contiene identificadores de clientes en claro ni datos personales.

## 4. Versionado semántico del modelo

Formato `MAJOR.MINOR.PATCH`, definido en `config.MODEL_VERSION` y escrito en el model card.

| Cambio | Sube | Ejemplo |
|---|---|---|
| Cambian las variables de entrada, el significado de una variable o el contrato de la API | **MAJOR** | agregar o quitar una feature |
| Se reentrena con datos nuevos o se cambia de algoritmo, con las mismas variables | **MINOR** | reentrenar por drift; pasar de regresión logística a random forest |
| Se corrige algo que no cambia el modelo ni sus métricas | **PATCH** | texto del model card, aviso de uso responsable |

- Un **cambio de datos o de features siempre genera una nueva versión** (constitución VI).
- No se reutiliza un número de versión: cada versión corresponde a un único archivo y huella.
- Cada predicción devuelve la versión que la generó (FR-004).
- Guardar la huella SHA-256 del `.joblib` en el model card, para que el servicio verifique su
  integridad al cargar (FR-021): **(pendiente, T090 y T070)**.

## 5. Disparadores de reentrenamiento

Revisión **trimestral** y, además, en cualquiera de estos casos (ASUM-DM §8):

| Disparador | Umbral | Fuente |
|---|---|---|
| Cambio de datos crítico en alguna variable | PSI ≥ 0,25 (alerta desde 0,10) | `drift.json` |
| Caída de recall sostenida | recall < 0,70 | evaluación periódica con datos etiquetados |
| Cambio de datos o de variables | cualquiera | decisión de Ciencia de Datos |
| Brecha de equidad | diferencia de recall entre grupos de edad > 0,05 | `evaluacion.json` |

Procedimiento:
1. Ciencia de Datos detecta el disparador y lo registra (fecha, evidencia).
2. Reentrena con `python -m churn.train` (semilla fija) y genera las evidencias de la sección 3.
3. Sube la versión según la sección 4.
4. El dueño del modelo aprueba o rechaza (sección 2).
5. Solo entonces se reemplaza el modelo servido.

El reentrenamiento **no es automático** (fuera de alcance de la spec): lo decide una persona.
Una alerta de PSI (0,10–0,25) no obliga a reentrenar, pero se anota y se vigila en el siguiente corte.

## 6. Retiro y reversión (rollback)

Cuándo retirar la versión servida:
- el servicio informa `no_sano` en `/health` de forma sostenida, o la huella no coincide;
- el recall medido cae por debajo de 0,70 y no hay una versión nueva aprobada;
- se detecta fuga de identificadores, uso indebido o un sesgo que incumple el criterio de equidad;
- una versión nueva aprobada falla en producción.

Procedimiento (manual):
1. **Declarar el retiro.** Ciencia de Datos avisa al dueño del modelo; este lo autoriza y se registra
   motivo y fecha.
2. **Elegir la versión de reversión:** la última versión **aprobada** cuyas evidencias sigan guardadas.
   Si no existe ninguna, se deja el servicio sin modelo: responde 503 y no entrega predicciones
   (FR-013), lo cual es preferible a servir un modelo no aprobado.
3. **Restaurar** `models/churn_model.joblib` y `models/model_card.json` de esa versión. Hoy
   `python -m churn.train` sobrescribe ambos archivos, así que **antes de entrenar** hay que copiar la
   versión vigente a un archivo aparte (por ejemplo `models/versiones/<versión>/`).
4. **Verificar:** reiniciar la API y comprobar `GET /health` (`sano`, versión esperada) y una
   predicción de prueba cuya `version_modelo` coincida.
5. **Cerrar:** anotar en el acta la versión retirada, la restaurada, el motivo y quién lo aprobó.
   Mantener las evidencias de la versión retirada para la auditoría.
6. **Informar** a Retención de que las listas generadas con la versión retirada deben revisarse.

Para un corte de emergencia sin versión de reversión, retirar `models/churn_model.joblib` y
reiniciar: la API arranca, `/health` responde 503 y `/predict` responde 503.

## 7. Uso responsable

- El modelo **apoya** la decisión de retención; no decide. Toda acción sobre un cliente requiere
  revisión humana de un analista de retención.
- No se usa para negar servicios, cambiar precios ni tomar decisiones automatizadas. Cada respuesta
  de la API incluye el aviso de uso responsable.
- **Sesgo:** `rango_edad` nunca es una variable del modelo; solo se usa para auditar el recall por
  grupo, con un solo umbral para todos (nunca umbrales por grupo). Hoy el criterio de equidad **no se
  cumple** (brecha de recall 0,147 frente al máximo de 0,05; grupo `60+` con 40 positivos en la prueba) y
  el intento de mitigación (`python -m churn.mitigacion`) no logró bajarla de 0,05 con ninguna variante
  (la mejor, sin `antiguedad_meses`, queda en 0,075). Se documenta y no se fuerza: el modelo se sirve con
  alerta y no es candidato a aprobación hasta resolverlo.
- **Regla del umbral (D4, FR-027):** el entrenamiento nunca aborta. Elige el umbral de mayor precision con
  recall ≥ 0,70 y, si ninguno lo alcanza, el de mayor recall; guarda siempre `criterios_cumplidos`,
  `razones_no_aprobado` y la `regla_umbral` aplicada.
- **Privacidad:** los registros guardan el identificador solo codificado con una sal que viene de la
  configuración, nunca en claro. Los datos del taller son sintéticos: no extrapolar resultados a
  clientes reales sin revalidar.

## 8. Trazabilidad

| Tema | Requisito | Tarea | Archivo |
|---|---|---|---|
| Versión por predicción | FR-004 | T022 | `src/churn/predict.py` |
| Estado y versión del servicio | FR-013 | T046 | `src/churn/api.py` (`/health`) |
| Registro sin identificadores | FR-015, FR-023 | T045, T047 | `src/churn/registro.py` |
| Cambio de datos (PSI) | FR-014 | T051–T055 | `src/churn/drift.py` |
| Integridad del modelo | FR-021 | T070 | pendiente |
| Equidad por edad | SC-010 | T015 | `src/churn/train.py`, `src/churn/evaluate.py` |
| Aprobación del dueño del modelo | constitución VI | T068 | `models/model_card.json` (`aprobacion`) |
