#!/usr/bin/env bash
# 直接运行源码（开发调试用）。优先使用项目内已装好依赖的 .venv。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-pytorch_m1}"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="$PYTHON_BIN"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PY="$SCRIPT_DIR/.venv/bin/python"
elif [[ -x "$HOME/miniforge3/envs/$CONDA_ENV_NAME/bin/python" ]]; then
  PY="$HOME/miniforge3/envs/$CONDA_ENV_NAME/bin/python"
else
  PY="$(conda run -n "$CONDA_ENV_NAME" which python)"
fi

exec "$PY" "$SCRIPT_DIR/main.py" "$@"
