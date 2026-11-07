# Plan B · Sin internet o laptops con pocos recursos

## Matriz rápida de decisión
| Situación | Solución | Tiempo |
|---|---|---|
| Sin internet en la sala | **Kit offline en USB** (sección A) | 10–15 min por equipo (hacerlo antes) |
| Laptop con 8 GB de RAM | Modelo **3B** `taller-coder-mini` (sección B1) | 3 min |
| Laptop con < 8 GB o muy lenta | **Servidor Ollama compartido** en la LAN (sección B2) | 2 min por equipo |
| Ollama u OpenCode no instalan | **Modo pareja** + archivos ya construidos de este repositorio (sección C) | inmediato |
| Spec Kit no instala | Plantillas manuales de `plantillas/` (sección D) | inmediato |
| Python/pip falla | Wheels locales (sección A3) o pareja | 5 min |

## A. Kit offline (preparar con internet, por sistema operativo)
1. **Instaladores**: VS Code, Python 3.12, Git, Node.js LTS, Ollama (Windows `.exe`, macOS `.dmg`/`.pkg`, Linux `.deb`/script).
2. **Modelo de Ollama**: en una máquina con el modelo descargado, copie la carpeta de modelos:
   - macOS/Linux: `~/.ollama/models` · Windows: `%USERPROFILE%\.ollama\models`
   - En el equipo destino, péguela en la misma ruta y ejecute `ollama list` (no requiere red). Luego `ollama create taller-coder -f Modelfile`.
3. **Dependencias de Python** (preparar wheels para el mismo SO y versión de Python de los asistentes):
   ```bash
   uv lock
   uv export --locked --extra dev --format requirements.txt --no-hashes --no-emit-project --output-file requirements-offline.txt
   pip download -r requirements-offline.txt -d wheels
   pip wheel "specify-cli @ git+https://github.com/github/spec-kit.git" -w wheels
   # Al terminar, borrar requirements-offline.txt (Windows PowerShell: Remove-Item requirements-offline.txt)
   # En el equipo sin red:
   uv sync --offline --find-links wheels --extra dev --locked
   uv tool install --offline --find-links wheels specify-cli
   ```
   El flujo normal es `uv sync --extra dev`. `pyproject.toml` declara las dependencias y `uv.lock` fija sus versiones;
   la exportación `requirements-offline.txt` es temporal y solo sirve para descargar wheels.
4. **OpenCode**: `npm pack opencode-ai` genera un `.tgz`; en el equipo destino `npm install -g ./opencode-ai-*.tgz`.
   Alternativa: copiar el binario `opencode` ya instalado (`which opencode` / `where opencode`).
   > El paquete npm descarga un binario específico de plataforma al instalarse; **pruebe la instalación offline antes del taller** en cada SO.
5. **Extensión de VS Code**: descargue el `.vsix` de OpenCode y Python desde el Marketplace e instálelos con
   `code --install-extension archivo.vsix`.
6. **Repositorio**: `taller-churn-mlops.zip` (incluye datos y modelo entrenado).
7. **Spec Kit sin red**: el scaffolding usa recursos incluidos en el paquete; en Windows requiere PowerShell 7 (`pwsh`).

## B. Pocos recursos
### B1. Modelo pequeño en la propia laptop
```bash
ollama pull qwen2.5-coder:3b
ollama create taller-coder-mini -f Modelfile.mini
```
En OpenCode: `/models` → **taller-coder-mini**. Consejos: cierre el navegador y otras apps, use prompts cortos (uno por archivo),
y si se queda sin memoria baje `num_ctx` a 8192 en `Modelfile.mini` y vuelva a crear el modelo.

### B2. Servidor Ollama compartido (laptop potente del facilitador)
En la laptop servidor (≥ 16 GB RAM, idealmente GPU):
```bash
# macOS/Linux
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_NUM_PARALLEL=4 ollama serve
# Windows PowerShell
$env:OLLAMA_HOST="0.0.0.0:11434"; $env:OLLAMA_NUM_PARALLEL="4"; ollama serve
```
En cada asistente, cambie en `opencode.json` la `baseURL` a `http://<IP-del-servidor>:11434/v1` y ejecute
`curl http://<IP>:11434/api/tags` para verificar. Abra el puerto 11434 en el firewall del servidor y use sólo una red de confianza.
Capacidad orientativa: 6–10 parejas por servidor con modelo 7B; más si usan el 3B.

## C. Modo pareja / sin IA
- Quien no tiene IA trabaja como **navegante**: lee la spec, revisa el código generado por la pareja y ejecuta las pruebas.
- Los archivos finales ya están en este repositorio (`src/churn/`, `tests/`). Quien no pueda generarlos con IA los lee y los ejecuta con `uv run pytest`, para no perder el hilo.
- Ejercicio equivalente sin IA: usar `prompts/PROMPTS_OPENCODE.md` como **checklist de revisión** del código de referencia.

## D. Spec Kit no disponible
Copie las plantillas y complételas a mano (mismos artefactos, mismo aprendizaje):
```bash
mkdir -p specs/002-campana-retencion-monitoreo .specify/memory
cp plantillas/spec_plantilla.md  specs/002-campana-retencion-monitoreo/spec.md
cp plantillas/plan_plantilla.md  specs/002-campana-retencion-monitoreo/plan.md
cp plantillas/tasks_plantilla.md specs/002-campana-retencion-monitoreo/tasks.md
```
Use la skill `spec-code-review` en lugar de `/speckit.converge`.

## E. Problemas frecuentes
| Síntoma | Causa probable | Solución |
|---|---|---|
| `connection refused :11434` | Ollama no está corriendo | `ollama serve` (o abrir la app Ollama) |
| OpenCode no ve el modelo | nombre distinto en `opencode.json` | `ollama list` y copiar el nombre exacto |
| El agente no usa herramientas / no edita archivos | contexto corto o modelo sin *tool calling* | usar `taller-coder` (num_ctx 16k); evitar modelos sin soporte de herramientas |
| Respuestas muy lentas | CPU sin GPU, RAM al límite | modelo 3B o servidor compartido |
| Archivos generados incompletos | límite de salida del modelo | prompt de rescate: "Continúa exactamente desde la línea …" |
| `uv` no se reconoce | uv no está instalado o no está en `PATH` | instalar uv y abrir una terminal nueva |
| Puerto 8000 ocupado | otra app | `uv run uvicorn churn.api:app --port 8001` |
| `ModuleNotFoundError: churn` | no se sincronizó/instaló el proyecto | `uv sync --extra dev` (o `uv sync --offline --find-links wheels --extra dev` sin internet) |
| `/speckit.*` no aparece | integración no instalada o OpenCode no reiniciado | `specify integration install opencode` y reiniciar OpenCode |
