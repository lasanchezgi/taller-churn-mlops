# Atajos para macOS/Linux. En Windows use: uv run python tareas.py <tarea>
.PHONY: datos entrenar entrenar-rf probar api trafico drift smoke todo limpiar
datos:       ; uv run python tareas.py datos
entrenar:    ; uv run python tareas.py entrenar
entrenar-rf: ; uv run python tareas.py entrenar-rf
probar:      ; uv run python tareas.py probar
api:         ; uv run python tareas.py api
trafico:     ; uv run python tareas.py trafico
drift:       ; uv run python tareas.py drift
smoke:       ; uv run python tareas.py smoke
todo:        ; uv run python tareas.py todo
limpiar:     ; uv run python tareas.py limpiar
