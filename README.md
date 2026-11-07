> **Repositorio del alumno**: el código de `src/churn/`, las pruebas y las especificaciones se construyen durante el taller con OpenCode y Spec Kit. Empieza por `plantillas/ASUM-DM_plantilla.md` y `prompts/PROMPTS_OPENCODE.md`. La solución está en `referencia/`.

# Taller · Churn Telco con ASUM-DM + SDD + ECC + OpenCode + MLOps

Repositorio plantilla del taller **"Integración de ASUM-DM, MLOps, Spec-Driven Development, skills ECC y modelos
abiertos con OpenCode en Visual Studio Code"**. Todo corre en tu laptop: **sin tokens, sin cuentas, sin nube**.

## Qué hace el proyecto
Un servicio que **apoya** al analista de retención de una telco. Recibe los datos de un cliente (antigüedad, plan,
cargo mensual, reclamos de los últimos 3 meses, uso de datos, método de pago y renovación) y devuelve la
**probabilidad de que cancele en los 60 días siguientes**, un **nivel de riesgo** (alto ≥ 0,70 · medio ≥ 0,50 · bajo < 0,50)
y una **recomendación** de un catálogo fijo. La edad nunca entra al modelo: solo sirve para auditar sesgo.

```
ASUM-DM (negocio) → Spec Kit (constitución, spec, plan, tareas) → código + pruebas → API → monitoreo → gobernanza
```

### Estado actual
El proyecto se construye paso a paso. Hoy funciona:

| Pieza | Estado | Comando |
|---|---|---|
| Datos sintéticos | listo | `uv run python -m churn.dataset` |
| Entrenamiento y model card | listo (`aprobado_para_despliegue = False`, ver §7) | `uv run python -m churn.train` |
| Pruebas | listo (80) | `uv run pytest` |
| `POST /predict` y `/docs` | listo | `uv run uvicorn churn.api:app --reload` |
| `/predict/lote`, `/campana/contactos`, `/health`, `/metrics`, `/drift`, `/dashboard` | **pendiente** (US3–US7, Fase 10 de `specs/002-campana-retencion-monitoreo/tasks.md`) | — |
| Registro de predicciones con hash, límite de solicitudes, comprobación de integridad del modelo | **pendiente** (Fase 12) | — |

> `tareas.py` y `Makefile` citan `churn.drift` y `scripts/simular_trafico.py`, que aún no funcionan hasta que se implementen esas piezas.

## Inicio rápido (solo el proyecto)
Necesitas Python 3.11+ y [uv](https://docs.astral.sh/uv/). Desde la raíz del repositorio:

**Windows (PowerShell)**
```powershell
winget install -e --id astral-sh.uv
uv sync --extra dev
```
**macOS**
```bash
brew install uv
uv sync --extra dev
```
**Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra dev
```
`uv sync` crea `.venv` e instala las dependencias. No hace falta activar el entorno: usa `uv run`. Comprueba:
```bash
uv run python -c "import churn; print('ok')"     # salida esperada: ok
```
Si prefieres instalar todas las herramientas del taller (VS Code, Ollama, OpenCode, Spec Kit), usa las secciones 2 y 3.

## Contenido
| Ruta | Qué es |
|---|---|
| `business/ASUM-DM.md` | Entendimiento de negocio completo (referencia) |
| `.specify/memory/constitution.md`, `specs/002-campana-retencion-monitoreo/` | Constitución, spec, plan, tareas y checklists (la 002 reemplaza a `specs/001-api-churn`) |
| `src/churn/` | Código hecho: `config`, `dataset`, `features`, `train`, `evaluate`, `predict`, `recomendaciones`, `api` |
| `tests/` | 80 pruebas pytest (datos, features, evaluación, entrenamiento, API) |
| `data/raw/churn_telco.csv` | Dataset sintético determinista (5.000 clientes, semilla 42) |
| `models/` | Modelo serializado + `model_card.json` |
| `dashboard/index.html` | Panel de métricas sin dependencias; lee `/metrics`, que aún no existe |
| `.opencode/skills/` | 6 skills estilo ECC: ML, testing, seguridad, arquitectura, docs, revisión vs spec |
| `opencode.json`, `Modelfile`, `AGENTS.md` | Configuración de OpenCode + Ollama local y reglas del agente |
| `prompts/PROMPTS_OPENCODE.md` | Prompts en español, listos para copiar |
| `plantillas/` | Plantillas ASUM-DM, spec, plan, tasks |
| `docs/` | Guion del facilitador, gobernanza, ética, rúbrica, plan B, checklist previo, reto |
| `scripts/` | Instaladores por SO, smoke test y simulador de tráfico |

## 1. Requisitos
- 16 GB de RAM recomendado (8 GB con el modelo 3B), 15 GB de disco libre.
- VS Code, Python 3.11+, Git, Node.js LTS, uv, Ollama, OpenCode, Spec Kit.

## 2. Instalación automática (recomendada)
Desde la raíz del repositorio:

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1        # laptop >= 16 GB
powershell -ExecutionPolicy Bypass -File scripts\instalar_windows.ps1 -Mini  # laptop de 8 GB
```
**macOS** (requiere [Homebrew](https://brew.sh))
```bash
bash scripts/instalar_macos.sh          # o: bash scripts/instalar_macos.sh --mini
```
**Linux (Ubuntu/Debian)**
```bash
bash scripts/instalar_linux.sh          # o: bash scripts/instalar_linux.sh --mini
```

## 3. Instalación manual paso a paso
| Paso | Windows (PowerShell) | macOS | Linux |
|---|---|---|---|
| VS Code | `winget install -e --id Microsoft.VisualStudioCode` | `brew install --cask visual-studio-code` | `sudo snap install code --classic` |
| Python 3.12 | `winget install -e --id Python.Python.3.12` | `brew install python@3.12` | `sudo apt install python3 python3-venv` |
| Git | `winget install -e --id Git.Git` | `brew install git` | `sudo apt install git` |
| Node.js | `winget install -e --id OpenJS.NodeJS.LTS` | `brew install node` | `sudo apt install nodejs npm` |
| uv | `winget install -e --id astral-sh.uv` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Ollama | `winget install -e --id Ollama.Ollama` | `brew install --cask ollama` | `curl -fsSL https://ollama.com/install.sh \| sh` |
| OpenCode | `npm install -g opencode-ai` | `curl -fsSL https://opencode.ai/install \| bash` | `curl -fsSL https://opencode.ai/install \| bash` |
| Spec Kit | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git` | igual | igual |

**Modelo local** (todos los SO):
```bash
ollama pull qwen2.5-coder:7b
ollama create taller-coder -f Modelfile        # contexto 16k y temperatura baja para OpenCode
# Laptop de 8 GB:
ollama pull qwen2.5-coder:3b && ollama create taller-coder-mini -f Modelfile.mini
```

**Extensiones de VS Code**: busca **OpenCode** y **Python** en el Marketplace e instálalas
(o `code --install-extension ms-python.python`). La extensión de OpenCode se activa al ejecutar `opencode`
en la terminal integrada (atajo: `Ctrl+Esc` en Windows/Linux, `Cmd+Esc` en macOS).

**Entorno del proyecto**
```bash
uv sync --extra dev
```
`uv sync` crea `.venv` si no existe e instala el proyecto con sus dependencias de desarrollo declaradas en
`pyproject.toml`. No es necesario activar el entorno: use `uv run` para ejecutar comandos dentro de él. El archivo
`uv.lock` fija las versiones; consérvelo y súbalo junto con el proyecto para que todos recreen el mismo entorno.

**Spec Kit en este repo** (crea `.opencode/commands/speckit.*`):
```bash
specify integration install opencode
# Si tu versión no lo reconoce: specify init --here --integration opencode
```

## 4. Smoke test
```bash
uv run python scripts/smoke_test.py            # verifica herramientas, Ollama, modelo y API
uv run python scripts/smoke_test.py --sin-ia   # sólo la parte Python (Plan B)
```
Salida esperada al final: `Todo listo para el taller.`

## 5. Configuración de OpenCode con Ollama
`opencode.json` (ya incluido) apunta a `http://localhost:11434/v1` con el proveedor `@ai-sdk/openai-compatible`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "ollama/taller-coder",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": { "taller-coder": { "name": "Taller - Qwen2.5-Coder 7B (ctx 16k)" } }
    }
  }
}
```
Abre VS Code en la carpeta, terminal integrada → `opencode` → `/models` → **taller-coder**.
Alternativa: `ollama launch opencode` (configura OpenCode con Ollama sin editar archivos).

> **Contexto**: la documentación de Ollama recomienda 64k de contexto para OpenCode. En laptops usamos 16k
> (`Modelfile`) con prompts cortos; si tienes ≥ 32 GB de RAM sube `num_ctx` a 32768 o más.

### Skills ECC
Las skills de `.opencode/skills/<nombre>/SKILL.md` siguen el formato estándar (`name`, `description`) y OpenCode
las descubre automáticamente; el agente las carga con su herramienta `skill`. Están inspiradas en
[Everything Claude Code (ECC)](https://github.com/affaan-m/ECC). Para usar el catálogo completo de ECC
(opcional, requiere internet) sigue su guía para OpenCode o copia skills de su carpeta `skills/` a `.opencode/skills/`.

## 6. Uso
Cada comando va con su salida esperada (real, de la última ejecución).

**1. Generar datos**
```bash
uv run python -m churn.dataset
```
```
5000 filas · escenario base · churn 24.7%
.../data/raw/churn_telco.csv ya existe; use --forzar para sobrescribirlo
```
No pisa el CSV existente. Para regenerarlo con este generador: `uv run python -m churn.dataset --forzar`
(la columna `periodo` del CSV original no se genera). El escenario de prueba de drift no escribe en `data/raw`:
`uv run python -m churn.dataset --escenario crisis` → `5000 filas · escenario crisis · churn 30.7%`.

**2. Entrenar**
```bash
uv run python -m churn.train                     # regresión logística (base)
uv run python -m churn.train --algoritmo rf      # Random Forest, solo si la base no cumple
```
```
logreg · umbral 0.538 · recall 0.734 · precision 0.493 · ROC-AUC 0.811
criterios: {'recall': True, 'precision': True, 'roc_auc': True, 'equidad_recall': False, 'tamano_grupos': True}
aprobado_para_despliegue = False
```
Escribe `models/churn_model.joblib`, `models/model_card.json` y `reports/metrics/evaluacion.json`.
Cumple recall, precision y ROC-AUC, pero **no** el criterio de equidad (brecha de recall entre grupos de edad 0,147 > 0,05),
así que el modelo no queda aprobado.

**3. Probar**
```bash
uv run pytest
```
```
80 passed in 0.9s
```

**4. Levantar la API**
```bash
uv run uvicorn churn.api:app --reload
```
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
Abre <http://localhost:8000/docs>. Si el puerto está ocupado, añade `--port 8001`. Deja la terminal abierta.
Necesita `models/churn_model.joblib` (paso 2); sin él, `/predict` responde 503.

**5. Consultar un cliente** (otra terminal)

macOS / Linux
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"antiguedad_meses": 6, "tipo_plan": "prepago", "cargo_mensual": 45.5, "reclamos_ult_3m": 3, "uso_datos_gb": 2.1, "metodo_pago": "efectivo", "renovo_contrato": "no"}'
```
Windows (PowerShell)
```powershell
$cuerpo = '{"antiguedad_meses": 6, "tipo_plan": "prepago", "cargo_mensual": 45.5, "reclamos_ult_3m": 3, "uso_datos_gb": 2.1, "metodo_pago": "efectivo", "renovo_contrato": "no"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body $cuerpo
```
```json
{"probabilidad_churn": 0.98, "nivel_riesgo": "alto",
 "recomendacion": "Contactar con oferta de retención; revisión humana antes de actuar",
 "version_modelo": "1.0.0",
 "aviso_uso_responsable": "Apoyo a la decisión: este resultado no es una decisión. Requiere revisión humana antes de actuar sobre el cliente."}
```
Un dato inválido devuelve 422. Por ejemplo, el cliente anterior con `"antiguedad_meses": 121` y un campo extra `"cedula"`:
```json
{"error": "Entrada inválida", "detalle": [
  {"campo": "antiguedad_meses", "mensaje": "debe ser menor o igual que 120"},
  {"campo": "cedula", "mensaje": "campo no previsto"}]}
```

**6. Ver el dashboard** — *pendiente*. `dashboard/index.html` ya existe, pero necesita `GET /metrics` y `GET /dashboard`
(tareas de la Fase 10 y US4). Hoy `http://localhost:8000/dashboard` responde 404.

| Endpoint | Estado | Propósito |
|---|---|---|
| `POST /predict` | listo | Un cliente → probabilidad, nivel, recomendación, versión y aviso |
| `GET /docs` | listo | Documentación interactiva |
| `POST /predict/lote`, `POST /campana/contactos`, `POST /drift` | pendiente | Lotes de hasta 1.000, lista de contacto, cambio de datos |
| `GET /health`, `GET /metrics`, `GET /dashboard` | pendiente | Salud, métricas agregadas y vista de solo lectura |

Contrato completo: `specs/002-campana-retencion-monitoreo/contracts/openapi.yaml`.

### Trazabilidad (lo hecho hasta ahora)
| Requisito | Tarea | Archivo | Prueba |
|---|---|---|---|
| FR-016 datos y entrenamiento reproducibles | T004, T009 | `src/churn/dataset.py`, `train.py` | `tests/unit/test_dataset.py`, `tests/integration/test_train.py` |
| FR-006, FR-008 validación y sin edad | T005, T010 | `src/churn/features.py`, `api.py` | `tests/unit/test_features.py`, `tests/integration/test_api_validacion.py` |
| FR-018, SC-010 métricas y equidad | T006, T011 | `src/churn/evaluate.py` | `tests/unit/test_evaluate.py` |
| FR-001..005, FR-007 predicción y errores | T020–T026 | `src/churn/api.py`, `predict.py` | `tests/test_api.py`, `tests/integration/test_api_predict.py` |

## 7. Uso responsable
- **Apoyo, no decisión**: el servicio no debe usarse para negar servicios, cambiar precios ni actuar sobre un cliente
  sin revisión humana. Cada respuesta incluye ese aviso.
- **Sesgo**: la edad no se usa para predecir y se audita por grupo (`18-25`, `26-40`, `41-60`, `60+`). Hoy la brecha de recall
  entre grupos es 0,147 (el criterio es ≤ 0,05): el modelo **no está aprobado** (`aprobado_para_despliegue = False`) y la
  aprobación humana del dueño del modelo sigue vacía en `model_card.json`. Con ~130 clientes en el grupo `60+` la medida es
  ruidosa; hay que revisarla antes de cualquier uso real.
- **Privacidad**: `id_cliente` es opcional, se usa solo para trazabilidad y no se devuelve en `/predict`. Los errores no repiten
  los valores enviados. El registro de predicciones con identificadores codificados (hash con sal) **aún no está implementado**;
  hasta entonces el servicio no registra identificadores.
- **Datos**: son sintéticos. Antes de usar datos reales hacen falta base legal, derechos de acceso y supresión, y autenticación.

Ver [docs/ETICA.md](docs/ETICA.md) y la [constitución](.specify/memory/constitution.md).
