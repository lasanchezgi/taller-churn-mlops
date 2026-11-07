---
name: spec-code-review
description: Revisa código contra spec.md, plan.md y tasks.md de Spec Kit, detecta brechas y propone tareas faltantes antes de /speckit.converge. Úsala al cerrar cada tarea.
license: MIT
compatibility: opencode
metadata:
  origen: taller-churn-mlops
  inspirado_en: everything-claude-code (ECC)
---
# Skill: revisión de código contra la especificación (estilo ECC · code-reviewer)

## Procedimiento
1. Lee `specs/002-campana-retencion-monitoreo/spec.md` (FR-xxx, SC-xxx) y `tasks.md`.
2. Para cada requisito, busca evidencia en el código **y** en las pruebas.
3. Construye la matriz de trazabilidad:

| Requisito | Archivo/función | Prueba | Estado (cumple/parcial/falta) |
|---|---|---|---|

4. Lista brechas como tareas nuevas con formato Spec Kit: `- [ ] T0xx [FR-xxx] descripción (archivo)`.
5. No reescribas código en esta revisión: sólo reporta. La corrección se hace en un paso aparte.

## Señales de alerta
- Código sin requisito asociado (alcance no pedido).
- Requisito sin prueba.
- Detalles técnicos en `spec.md` (deben ir en `plan.md`).
