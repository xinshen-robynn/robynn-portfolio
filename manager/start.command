#!/bin/zsh
set -e
SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
VENV_DIR="$PROJECT_DIR/.portfolio-manager-venv"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
cd "$PROJECT_DIR"
if [[ ! -x "$PYTHON_BIN" ]]; then PYTHON_BIN="$(command -v python3)"; fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Preparing Portfolio Manager for the first time..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt"
fi
echo "Starting Portfolio Manager..."
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/server.py"
