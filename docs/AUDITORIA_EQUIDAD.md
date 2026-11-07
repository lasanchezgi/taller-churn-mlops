# Auditoría trimestral de equidad

Procedimiento para cumplir FR-025 (T087) y definir la revisión humana de FR-005. Complementa
`docs/ETICA.md` y la sección 7 de `docs/GOBERNANZA.md`.

**Por qué existe.** El servicio no recibe la edad (`rango_edad` se rechaza como campo no previsto), así que
no puede medir su propia equidad en producción. La edad solo la tiene el sistema de origen. Cada trimestre,
Ciencia de Datos cruza las predicciones reales con ese dato y reporta las diferencias entre grupos.

## 1. Responsables

| Rol | Hace |
|---|---|
| Ciencia de Datos (R) | Ejecuta la auditoría y redacta el informe |
| Dueño del modelo (A) | Revisa el informe y decide: continuar, mitigar, reentrenar o retirar |
| Gobernanza/Legal (C) | Revisa que el cruce con la edad cumpla la política de datos |
| Retención (C) | Aporta el resultado de las campañas del trimestre |

## 2. Entradas

- `logs/predicciones.jsonl` del trimestre: solo trae `id_codificado`, probabilidad, nivel y versión. No trae edad ni datos del cliente.
- La edad (`rango_edad`) y la baja real (`churn`) del sistema de origen, para los mismos clientes.
- La sal `CHURN_HASH_SALT` vigente durante el trimestre, para repetir el codificado del identificador y poder cruzar.
- `models/model_card.json` de la versión servida (umbral y métricas de referencia).

Acceso: el registro solo lo lee el equipo de Ciencia de Datos (FR-023). El cruce se hace en un entorno controlado y
**el resultado intermedio con edad e identificadores no se guarda** fuera de él. Las líneas de más de 90 días ya se
eliminaron del registro (`config.RETENCION_REGISTRO_DIAS`): hay que ejecutar la auditoría antes de que venzan las del
primer mes del trimestre, o exportar los agregados mensualmente.

## 3. Procedimiento

1. **Preparar el cruce.** Para cada cliente del sistema de origen, calcular `id_codificado` con la misma sal
   (`Registro.codificar`) y unirlo con el registro. Descartar predicciones sin identificador (`id_codificado = null`) y
   anotar cuántas fueron.
2. **Verificar cobertura.** Reportar cuántos clientes se pudieron cruzar y el tamaño de cada grupo de edad
   (`18-25`, `26-40`, `41-60`, `60+`). Un grupo con menos de `MIN_GRUPO_AUDITORIA` (100) clientes no permite concluir:
   se informa y se acumula con el trimestre siguiente.
3. **Calcular por grupo**, con el umbral de decisión del model card (un solo umbral para todos):
   - Tasa de selección (clientes con nivel alto o predicción positiva / clientes del grupo).
   - Recall y precision, sobre los clientes con baja real conocida.
   - Reparto de los contactados del trimestre frente al peso de cada grupo en la base.
4. **Comparar con los criterios** (SC-010):
   - Diferencia máxima de recall entre grupos ≤ `MAX_DIF_RECALL` (0,05).
   - Ratio de impacto dispar (menor tasa de selección / mayor) ≥ `MIN_RATIO_IMPACTO` (0,80).
5. **Medir la incertidumbre.** Con grupos pequeños, dar el error estándar de la diferencia de recall (en la prueba actual,
   `60+` tiene 40 positivos y el error de la diferencia con `18-25` es ≈ 0,09). Una diferencia menor que dos errores
   estándar se reporta como «no concluyente», no como «sin sesgo».
6. **Revisar proxies.** Repetir `python -m churn.mitigacion` con los datos del trimestre y comparar `revision_proxies`
   (`metodo_pago`, `tipo_plan`, `antiguedad_meses`) con la del model card.
7. **Redactar el informe** (plantilla en la sección 4) y entregarlo al dueño del modelo.

## 4. Informe del trimestre

| Campo | Contenido |
|---|---|
| Periodo y versión del modelo | |
| Clientes cruzados / sin cruzar | |
| Tamaño por grupo de edad | |
| Recall, precision y tasa de selección por grupo | |
| Diferencia máxima de recall y ratio de impacto dispar | |
| Error estándar y conclusión (cumple / no cumple / no concluyente) | |
| Efecto en las campañas (contactados por grupo frente al peso del grupo) | |
| Decisión del dueño del modelo, nombre y fecha | |

Si algún criterio no se cumple, se aplica el procedimiento de `docs/GOBERNANZA.md` (§1 y §5): el modelo sigue sirviéndose
con la alerta de equidad, no se relajan criterios y el dueño decide si mitigar, reentrenar o retirar.

## 5. Revisión humana de la lista de contacto (FR-005)

Ninguna lista de `POST /campana/contactos` se usa tal cual. Antes de contactar a un cliente:

1. Un **analista de retención** revisa la lista completa y la aprueba o la ajusta.
2. El proceso de campaña registra **el nombre del analista y la fecha** de la aprobación. Este registro vive en el
   proceso de campaña, no en la API: el servicio no guarda quién aprobó.
3. El analista confirma que ninguna acción niega servicio, cambia precios ni empeora condiciones (`docs/ETICA.md`).
4. Si el modelo está en estado «no aprobado» (`/health` → `aprobado_para_despliegue = false`), la lista lleva la alerta
   de equidad y el analista deja constancia de que la leyó.
5. La edad no se usa para decidir ni para fijar umbrales por grupo.
