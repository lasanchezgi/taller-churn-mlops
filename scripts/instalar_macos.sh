#!/usr/bin/env bash
# Instalación del entorno del taller en macOS (requiere Homebrew: https://brew.sh)
# Uso: bash scripts/instalar_macos.sh [--mini]   (--mini = modelo 3B para equipos de 8 GB)
set -euo pipefail
cd "$(dirname "$0")/.."   # ejecutar siempre desde la raíz del repo
MODELO="qwen2.5-coder:7b"; MF="Modelfile"; NOMBRE="taller-coder"
if [[ "${1:-}" == "--mini" ]]; then MODELO="qwen2.5-coder:3b"; MF="Modelfile.mini"; NOMBRE="taller-coder-mini"; fi

command -v brew >/dev/null || { echo "Instale Homebrew primero: https://brew.sh"; exit 1; }
echo "==> 1/7 VS Code, Ollama, Python 3.12, Git, Node.js, uv"
# Cask sólo si falta (evita errores si ya se instaló a mano)
[[ -d "/Applications/Visual Studio Code.app" ]] || command -v code >/dev/null || brew install --cask visual-studio-code
command -v ollama >/dev/null || [[ -d /Applications/Ollama.app ]] || brew install --cask ollama
brew install python@3.12 git node uv

echo "==> 2/7 OpenCode"
command -v opencode >/dev/null || curl -fsSL https://opencode.ai/install | bash

echo "==> 3/7 Spec Kit (specify-cli)"
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git || uv tool upgrade specify-cli

echo "==> 4/7 Extensiones de VS Code"
# 'code' puede no estar en el PATH justo tras instalar VS Code
CODE="$(command -v code || true)"
[[ -z "$CODE" ]] && CODE="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
"$CODE" --install-extension ms-python.python || echo "   Instale 'Python' desde el Marketplace de VS Code"
"$CODE" --install-extension sst-dev.opencode || echo "   Instale 'OpenCode' desde el Marketplace de VS Code"

echo "==> 5/7 Modelo local ($MODELO)"
OLLAMA="$(command -v ollama || echo /Applications/Ollama.app/Contents/Resources/ollama)"
pgrep -x ollama >/dev/null || (nohup "$OLLAMA" serve >/dev/null 2>&1 &)
for _ in $(seq 1 30); do   # espera hasta 30 s a que el servidor responda
  curl -fs http://localhost:11434/api/version >/dev/null && break; sleep 1
done
curl -fs http://localhost:11434/api/version >/dev/null || { echo "Ollama no respondió"; exit 1; }
"$OLLAMA" pull "$MODELO"
"$OLLAMA" create "$NOMBRE" -f "$MF"

echo "==> 6/7 Entorno Python del proyecto"
uv sync --extra dev

echo "==> 7/7 Smoke test"
uv run python scripts/smoke_test.py
