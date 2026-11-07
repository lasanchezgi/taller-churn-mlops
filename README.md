> **Repositorio del alumno**: el código de `src/churn/`, las pruebas y las especificaciones se construyen durante el taller con OpenCode y Spec Kit. Empieza por `plantillas/ASUM-DM_plantilla.md` y `prompts/PROMPTS_OPENCODE.md`. Este repositorio ya contiene la solución construida.

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
Todo lo de la especificación `specs/002-campana-retencion-monitoreo/` está implementado y probado (333 pruebas, 349 con el extra opcional de seguimiento):

| Pieza | Estado | Comando |
|---|---|---|
| Datos sintéticos (el CSV existente es la fuente de verdad, D6) | listo | `uv run python -m churn.dataset` |
| Entrenamiento y model card con huella (`hash_modelo`) | listo; `aprobado_para_despliegue = False` (ver §7) | `uv run python -m churn.train` |
| Pruebas | listo (**333**; 349 con el extra `mlflow`) | `uv run pytest` |
| `POST /predict`, `POST /predict/lote`, `POST /campana/contactos` | listo | `uv run uvicorn churn.api:app` |
| `GET /health`, `GET /metrics`, `GET /dashboard`, `POST` y `GET /drift` | listo | ídem |
| Registro con id hasheado, límite de solicitudes por IP, integridad del modelo | listo | automático al levantar la API |
| Simulación de cambio de datos y de tráfico | listo | `uv run python -m churn.drift --escenario crisis` · `uv run python scripts/simular_trafico.py` |

Pendiente de personas, no de código: textos definitivos de Retención y Legal (T064), aprobación del dueño del modelo (T068) y revisión por pares del ASUM-DM.

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
`uv sync` crea `.venv` e instala las dependencias; el grupo `dev` (pytest, httpx) se instala también con `uv sync` a secas y con `--extra dev`. No hace falta activar el entorno: usa `uv run`. Comprueba:
```bash
uv run python -c "import churn; print('ok')"     # salida esperada: ok
```
Si prefieres instalar todas las herramientas del taller (VS Code, Ollama, OpenCode, Spec Kit), usa las secciones 2 y 3.

## Contenido
| Ruta | Qué es |
|---|---|
| `business/ASUM-DM.md` | Entendimiento de negocio completo (referencia) |
| `.specify/memory/constitution.md`, `specs/002-campana-retencion-monitoreo/` | Constitución, spec, plan, tareas y checklists (la 002 reemplaza a `specs/001-api-churn`) |
| `src/churn/` | Código: `config`, `dataset`, `features`, `train`, `evaluate`, `mitigacion`, `predict`, `campana`, `drift`, `metricas`, `registro`, `limitador`, `recomendaciones`, `api` |
| `tests/` | 349 pruebas pytest con el extra opcional (333 sin él; las 16 de seguimiento se omiten solas): 191 unitarias (`tests/unit/`), 150 de integración (`tests/integration/`) y 8 de contrato de la API (`tests/test_api.py`) |
| `data/raw/churn_telco.csv` | Dataset sintético determinista (5.000 clientes, semilla 42) |
| `models/` | Modelo serializado + `model_card.json` |
| `dashboard/index.html` | Panel de solo lectura sin dependencias; lo sirve `GET /dashboard` y lee `/health` y `/metrics` |
| `.opencode/skills/` | 6 skills estilo ECC: ML, testing, seguridad, arquitectura, docs, revisión vs spec |
| `opencode.json`, `Modelfile`, `AGENTS.md` | Configuración de OpenCode + Ollama local y reglas del agente |
| `prompts/PROMPTS_OPENCODE.md` | Prompts en español, listos para copiar |
| `plantillas/` | Plantillas ASUM-DM, spec, plan, tasks |
| `docs/` | Gobernanza, ética, auditoría (`AUDITORIA.md`, `AUDITORIA_EQUIDAD.md`), decisiones (`DECISIONES.md`), rúbrica, plan B, checklist previo, reto |
| `scripts/` | Instaladores por SO, smoke test y simulador de tráfico |
| `Makefile`, `tareas.py`, `Dockerfile` | Atajos (`make probar`), versión multiplataforma y imagen opcional (§8) |

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

**Spec Kit en este repo (D9).** El repositorio trae la integración `claude` (`.claude/skills/`, comandos con guion) y no se reinstala nada.
Los dos nombres son equivalentes; usa el de tu herramienta:

| Paso | Claude Code | OpenCode |
|---|---|---|
| Constitución | `/speckit-constitution` | `/speckit.constitution` |
| Especificar | `/speckit-specify` | `/speckit.specify` |
| Plan y tareas | `/speckit-plan` · `/speckit-tasks` | `/speckit.plan` · `/speckit.tasks` |
| Revisar y converger | `/speckit-analyze` · `/speckit-converge` | `/speckit.analyze` · `/speckit.converge` |
| Implementar | `/speckit-implement` | `/speckit.implement` |

Para usar los comandos `/speckit.*` en OpenCode hay que instalar esa integración (crea `.opencode/commands/`):
`specify integration install opencode`. Los `prompts/PROMPTS_OPENCODE.md` están escritos con esa variante.

## 4. Smoke test
```bash
uv run python scripts/smoke_test.py            # verifica herramientas, Ollama, modelo y API
uv run python scripts/smoke_test.py --sin-ia   # sólo la parte Python (Plan B)
```
Salida esperada de `--sin-ia` (el bloque de Python; las líneas de herramientas dependen de tu equipo):
```
== Python: dependencias y pipeline ==
[OK] Dependencias (pandas, scikit-learn, fastapi)
[OK] Dataset data/raw/churn_telco.csv
[OK] API /health estado=sano modelo v1.0.0
[OK] API /predict p=0.9787896116200316 riesgo=alto

Todo listo para el taller.
```
Sin `--sin-ia`, si Ollama no está activo, la verificación obligatoria `Servidor Ollama activo` falla: ejecuta `ollama serve`.

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
Cada comando va con su salida esperada (real, de la última ejecución; rutas y números de proceso varían). Los comandos funcionan tal cual en macOS.

**1. Generar datos**
```bash
uv run python -m churn.dataset
```
```
5000 filas · escenario base · churn 24.7%
/ruta/al/repo/data/raw/churn_telco.csv ya existe; use --forzar para sobrescribirlo
```
`data/raw/churn_telco.csv` es la **fuente de verdad** (D6): es un insumo con 25,5 % de churn y una columna `periodo`, no la salida del generador. Por eso el
comando no lo pisa. El generador (`churn.dataset.generar`) es solo para demos y pruebas; `--forzar` lo reemplaza con datos generados (24,7 %) y cambia las cifras del
ASUM-DM. El escenario de crisis no escribe en `data/raw`: `uv run python -m churn.dataset --escenario crisis` → `5000 filas · escenario crisis · churn 30.7%`.

**2. Entrenar**
```bash
uv run python -m churn.train                     # regresión logística (base)
uv run python -m churn.train --algoritmo rf      # Random Forest, solo si la base no cumple
```
```
logreg · umbral 0.538 · recall 0.734 · precision 0.493 · ROC-AUC 0.811
criterios: {'recall': True, 'precision': True, 'precision_top': True, 'roc_auc': True, 'roi': True, 'equidad_recall': False, 'ratio_impacto_dispar': True, 'tamano_grupos': True}
aprobado_para_despliegue = False
  no aprobado: brecha de recall entre grupos de edad 0.147 > 0.05 (18-25: 0.797; 60+: 0.650)
```
Escribe `models/churn_model.joblib`, `models/model_card.json` (con `hash_modelo`, el SHA-256 del `.joblib`) y `reports/metrics/evaluacion.json`. Cumple los 5 criterios
de la constitución, pero **no** el de equidad, así que el modelo no queda aprobado (ver §7). Reentrenar cambia el `.joblib` byte a byte (lleva la fecha): se versiona
junto con su `model_card.json`.

**3. Probar**
```bash
uv run pytest
```
```
...................................................                      [100%]
333 passed, 3 skipped in 14.18s
```
(`-q` está activado en `pyproject.toml`; la barra de puntos ocupa varias líneas.)

**4. Levantar la API**
```bash
uv run uvicorn churn.api:app
```
```
INFO:     Started server process [5187]
INFO:     Waiting for application startup.
falta CHURN_HASH_SALT: se usa la sal de desarrollo
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
Abre <http://localhost:8000/docs>. Añade `--reload` mientras desarrollas y `--port 8001` si el puerto está ocupado. Deja la terminal abierta. Necesita
`models/churn_model.joblib` **y** su `models/model_card.json` con la huella (paso 2): sin ellos, o con el modelo alterado, `/predict` responde 503 y `/health` `no_sano`.
La línea «falta CHURN_HASH_SALT» desaparece al exportar la sal (§8): `CHURN_HASH_SALT='una-frase-larga' uv run uvicorn churn.api:app`.

**5. Consultar un cliente** (otra terminal)

macOS / Linux
```bash
curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"antiguedad_meses": 6, "tipo_plan": "prepago", "cargo_mensual": 45.5, "reclamos_ult_3m": 3, "uso_datos_gb": 2.1, "metodo_pago": "efectivo", "renovo_contrato": "no"}'
```
Windows (PowerShell)
```powershell
$cuerpo = '{"antiguedad_meses": 6, "tipo_plan": "prepago", "cargo_mensual": 45.5, "reclamos_ult_3m": 3, "uso_datos_gb": 2.1, "metodo_pago": "efectivo", "renovo_contrato": "no"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body $cuerpo
```
```json
{"probabilidad_churn":0.9787896116200316,"nivel_riesgo":"alto","recomendacion":"Contactar con oferta de retención; revisión humana antes de actuar","version_modelo":"1.0.0","aviso_uso_responsable":"Apoyo a la decisión: este resultado no es una decisión. Requiere revisión humana antes de actuar sobre el cliente.","alerta_equidad":"Alerta de equidad: modelo no aprobado para despliegue (brecha de recall entre grupos de edad 0.147 > 0.05 (18-25: 0.797; 60+: 0.650)). Úselo solo como apoyo con revisión humana."}
```
`alerta_equidad` aparece mientras el modelo no esté aprobado (D2). Un dato inválido devuelve 422 sin repetir el valor recibido. Por ejemplo, el cliente anterior con `"antiguedad_meses": 121` y un campo extra `"cedula"`:
```json
{"error":"Entrada inválida","detalle":[{"campo":"antiguedad_meses","mensaje":"debe estar entre 1 y 120"},{"campo":"cedula","mensaje":"campo no previsto"}]}
```
Más de 60 solicitudes por minuto desde la misma IP devuelven 429 con `{"error": "Demasiadas solicitudes; reintente en N s"}` y la cabecera `Retry-After`.

**6. Estado del servicio**
```bash
curl -s http://localhost:8000/health
```
```json
{"estado":"sano","modelo_cargado":true,"version_modelo":"1.0.0","aprobado_para_despliegue":false,"alertas":["brecha de recall entre grupos de edad 0.147 > 0.05 (18-25: 0.797; 60+: 0.650)"],"error":null}
```
`estado` describe solo la salud operativa. Un modelo alterado da `503` con `"estado":"no_sano"`.

**7. Campaña, cambio de datos y dashboard**
```bash
uv run python scripts/simular_trafico.py --escenario crisis --n 500    # con la API arriba
uv run python -m churn.drift --escenario crisis
```
```
[ok] 500 clientes (crisis) enviados. Abra http://localhost:8000/dashboard
```
```
escenario crisis · estado general: critico · evaluar reentrenamiento
  cargo_mensual      PSI 0.227  alerta
  reclamos_ult_3m    PSI 3.275  critico
  (las otras 5 variables: estable)
  recall     base 0.734 → crisis 0.868
  precision  base 0.493 → crisis 0.399
```
Abre <http://localhost:8000/dashboard> (solo lectura). La crisis cambia las entradas, no las etiquetas de churn, por eso el recall *sube*: mide el efecto sobre las variables, no un churn nuevo.

**Atajos** (`make` en macOS/Linux; en Windows `uv run python tareas.py <tarea>`): `make datos`, `entrenar`, `entrenar-rf`, `probar`, `api`, `trafico`, `drift`, `smoke`, `todo`, `limpiar` (y `mlflow-ui`, ver abajo).

| Endpoint | Propósito |
|---|---|
| `POST /predict` | Un cliente → probabilidad, nivel, recomendación, versión y aviso |
| `POST /predict/lote` | Hasta 1.000 clientes, mismo orden, más el resumen de riesgo (mínimo 20 clientes) |
| `POST /campana/contactos` | Lote de hasta 5.000 con presupuesto y costo por contacto → lista de contacto por ingreso esperado |
| `POST /drift` · `GET /drift` | Compara un lote con la referencia de entrenamiento (PSI) · último informe |
| `GET /health` · `GET /metrics` · `GET /dashboard` | Salud, métricas agregadas sin identificadores y vista de solo lectura |
| `GET /docs` | Documentación interactiva |

En `/metrics`, `latencia_ms` mide solo la puntuación del modelo (no la validación ni la serialización) sobre las últimas 1.000 predicciones del proceso, y `roi_esperado` es una estimación, no el ROI incremental del ASUM-DM (que exige grupo de control).

Contrato completo: `specs/002-campana-retencion-monitoreo/contracts/openapi.yaml`. Escenarios de uso: `specs/002-campana-retencion-monitoreo/quickstart.md`.

### Seguimiento de experimentos (opcional)
Capa **opcional y local** (D11): sin ella todo funciona igual. La API nunca la usa; sigue cargando `models/churn_model.joblib` con su huella.
Guarda todo en `mlflow.db` y `mlruns/` (ignorados por git), sin servidor ni cuentas.

```bash
uv sync --extra dev --extra mlflow                 # instala el extra (un `uv sync` sin él lo quita)
uv run python -m churn.train --mlflow              # regresión logística → experimento «churn-retencion»
uv run python -m churn.train --algoritmo rf --mlflow
uv run python -m churn.drift --escenario crisis --mlflow   # experimento «churn-drift»
make mlflow-ui                                     # = mlflow ui --backend-store-uri sqlite:///mlflow.db → http://127.0.0.1:5000
# En macOS el puerto 5000 suele estar ocupado por AirPlay: use  uv run mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5001
```
- Cada entrenamiento deja **una corrida** con parámetros, métricas (técnicas, de negocio y de equidad), etiquetas (`version_modelo`, `hash_dataset`, `aprobado_para_despliegue`, `criterios_cumplidos`), la ficha, la matriz de confusión y el reporte de equidad, y registra el modelo `churn-retencion` con el alias `candidato`. El ejemplo de entrada no lleva `id_cliente` ni `rango_edad`.
- **Comparar LR frente a RF**: en <http://127.0.0.1:5000> abre «churn-retencion», marca las dos corridas y pulsa *Compare*; mira `recall`, `precision_top_5pct`, `dif_max_recall` y `ratio_impacto_dispar`. Tras un `--algoritmo rf --mlflow` vuelve a correr `python -m churn.train` si quieres dejar como servido el modelo de regresión logística: el entrenamiento sobrescribe `models/`.
- **Promover**: `uv run python scripts/promover_modelo.py` asigna el alias `produccion` solo si la ficha de la versión candidata dice `aprobado_para_despliegue=true`; con `--forzar --motivo "…"` se hace una excepción y el motivo queda como etiqueta. El entrenamiento nunca asigna `produccion`. El alias es un registro: no cambia el modelo que sirve la API. Ver [docs/GOBERNANZA.md](docs/GOBERNANZA.md).

### Trazabilidad (resumen)
| Requisito | Tarea | Archivo | Prueba |
|---|---|---|---|
| FR-016 reproducibilidad | T004, T009, T015 | `dataset.py`, `train.py` | `tests/unit/test_dataset.py`, `tests/integration/test_train.py` |
| FR-006..008 validación, sin edad | T005, T010, T013 | `features.py`, `api.py` | `test_features.py`, `test_api_validacion.py`, `test_id_cliente.py` |
| FR-001..005 predicción y aviso | T020–T026 | `api.py`, `predict.py` | `test_api_predict.py`, `tests/test_api.py` |
| FR-009..012 lote y campaña | T027–T041 | `campana.py`, `api.py` | `test_api_lote.py`, `test_api_campana.py`, `test_campana.py` |
| FR-013, FR-014 salud y cambio de datos | T043–T055 | `drift.py`, `api.py` | `test_api_drift.py`, `test_drift.py` |
| FR-015, FR-023 registro | T044, T045, T047, T072, T081 | `registro.py`, `api.py` | `test_api_registro.py`, `test_registro_campos.py` |
| FR-020 límite · FR-021 integridad · FR-022 errores | T069–T071, T077–T080 | `limitador.py`, `predict.py`, `api.py` | `test_limitador.py`, `test_integridad_modelo.py`, `test_api_errores.py` |
| FR-018, FR-024, SC-010 métricas y equidad | T006, T011, T082, T083 | `evaluate.py`, `train.py`, `mitigacion.py` | `test_evaluate.py`, `test_equidad.py` |
| FR-003, FR-017 recomendaciones | T018, T076, T086 | `recomendaciones.py` | `test_recomendaciones_terminos.py` |

## 7. Uso responsable
- **Apoyo, no decisión**: el servicio no debe usarse para negar servicios, cambiar precios ni actuar sobre un cliente
  sin revisión humana. Cada respuesta incluye ese aviso.
- **Sesgo**: la edad no se usa para predecir y se audita por grupo (`18-25`, `26-40`, `41-60`, `60+`). Hoy la brecha de recall
  entre grupos es 0,147 (el criterio es ≤ 0,05): el modelo **no está aprobado** (`aprobado_para_despliegue = False`) y la
  aprobación humana del dueño del modelo sigue vacía en `model_card.json`. Con ~130 clientes en el grupo `60+` la medida es
  ruidosa; hay que revisarla antes de cualquier uso real.
- **Privacidad**: `id_cliente` es opcional (hasta 64 caracteres: letras, números, guion y guion bajo), se usa solo para trazabilidad y no se devuelve en `/predict`.
  Los errores no repiten los valores enviados ni muestran trazas. Cada predicción escribe una línea en `logs/predicciones.jsonl` con solo `fecha`, `id_codificado`
  (SHA-256 con sal, 16 caracteres), `probabilidad_churn`, `nivel_riesgo` y `version_modelo`; sin identificador se guarda `null`.
- **Datos**: son sintéticos. Antes de usar datos reales hacen falta base legal, derechos de acceso y supresión, y autenticación.

Ver [docs/ETICA.md](docs/ETICA.md) y la [constitución](.specify/memory/constitution.md).

## 8. Seguridad, privacidad y paso a producción
**Secreto del codificado.** El identificador se guarda como `SHA-256(sal + id)`. La sal sale de la variable de entorno `CHURN_HASH_SALT`:
```bash
export CHURN_HASH_SALT='una-frase-larga-y-secreta'    # macOS / Linux
uv run uvicorn churn.api:app
```
Sin ella el servicio avisa y usa una sal de desarrollo (no usar en producción). No la guardes en el repositorio. Si la cambias, los códigos anteriores dejan de cruzar
con los nuevos; la auditoría trimestral (`docs/AUDITORIA_EQUIDAD.md`) necesita la sal vigente del trimestre.

**Retención.** `logs/predicciones.jsonl` conserva 90 días (`config.RETENCION_REGISTRO_DIAS`); las líneas más viejas se eliminan al arrancar y cada hora. Solo lo lee Ciencia de Datos.
`logs/*.jsonl` está en `.gitignore`.

**Acceso solo local del taller.** El servicio escucha en `127.0.0.1`, sin autenticación, con datos sintéticos. El límite de 60 solicitudes por minuto por IP
(`config.LIMITE_SOLICITUDES_POR_MINUTO`) vive en memoria de un solo proceso, no es una defensa de red, y usa la IP del socket (no confía en `X-Forwarded-For`).

**Integridad del modelo.** Al cargar, el servicio calcula el SHA-256 de `churn_model.joblib` y lo compara con `hash_modelo` de `models/model_card.json` *antes* de
deserializarlo. Si no coincide o falta, no sirve el modelo.

**Versionado de artefactos (T102).** `models/` y `reports/metrics/` se versionan: la API necesita el modelo para arrancar y su huella debe viajar con él. `data/processed/` y `logs/*.jsonl` no.

**Docker (opcional).** Hay un `Dockerfile` sin cuentas ni registros: `docker build -t churn-api .` y `docker run -p 8000:8000 -e CHURN_HASH_SALT=... churn-api`.
No se ha construido en este equipo (el demonio de Docker no estaba activo); se validó solo que la instalación editable resuelve `models/` desde `/app`.

**Antes de producción** (no cubierto por este taller): autenticación y control de acceso por rol; TLS y un proxy que fije la IP real del cliente para el límite;
base legal, derechos de acceso, rectificación y supresión sobre los datos (`docs/ETICA.md`); textos definitivos de Retención y Legal; revisión por pares del ASUM-DM;
aprobación del dueño del modelo (`aprobacion` en el model card); y resolver la brecha de equidad o aceptarla de forma explícita. Detalle en `docs/GOBERNANZA.md`.
