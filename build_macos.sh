#!/usr/bin/env bash
# 构建独立的 macOS .app（Qt 版）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONDA_ENV_NAME="${CONDA_ENV_NAME:-pytorch_m1}"

# 解释器选择：PYTHON > CONDA_PYTHON > 常用 conda 环境 > PATH 中的 python3
if [[ -n "${PYTHON:-}" ]]; then
  BASE_PYTHON="$PYTHON"
elif [[ -n "${CONDA_PYTHON:-}" && -x "$CONDA_PYTHON" ]]; then
  BASE_PYTHON="$CONDA_PYTHON"
elif [[ -x "$HOME/miniforge3/envs/$CONDA_ENV_NAME/bin/python" ]]; then
  BASE_PYTHON="$HOME/miniforge3/envs/$CONDA_ENV_NAME/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  BASE_PYTHON="$(command -v python3)"
else
  echo "找不到 Python 3.10+ 解释器。请用 PYTHON=/path/to/python3 指定。" >&2
  exit 1
fi

if ! "$BASE_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "需要 Python 3.10+，当前: $("$BASE_PYTHON" --version 2>&1)" >&2
  exit 1
fi

BUILD_VENV="$SCRIPT_DIR/.venv"

if [[ ! -x "$BUILD_VENV/bin/python" ]]; then
  # 隔离 site-packages：某些 conda 环境装有废弃的 pathlib 反向移植包，会阻断 PyInstaller。
  echo "==> 创建构建环境（基于 $BASE_PYTHON）"
  "$BASE_PYTHON" -m venv "$BUILD_VENV"
fi

echo "==> 安装构建依赖"
"$BUILD_VENV/bin/python" -m pip install --quiet --upgrade pip
"$BUILD_VENV/bin/python" -m pip install --quiet -r requirements-dev.txt

echo "==> 生成图标"
"$BUILD_VENV/bin/python" scripts/make_icon.py

echo "==> 清理旧产物（仅 Qt 版）"
rm -rf "$SCRIPT_DIR/build/PdfDigitizer" "$SCRIPT_DIR/dist/PDF Digitizer.app"

echo "==> PyInstaller 打包"
"$BUILD_VENV/bin/python" -m PyInstaller --noconfirm --clean PdfDigitizer.spec

APP_PATH="$SCRIPT_DIR/dist/PDF Digitizer.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "构建失败：未找到 $APP_PATH" >&2
  exit 1
fi

echo "==> 完成: $APP_PATH"
echo "   双击运行，或执行: open \"$APP_PATH\""
