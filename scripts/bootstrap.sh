#!/usr/bin/env bash
set -euo pipefail

# Bootstrap project development environment
# - creates .venv if missing
# - upgrades pip/tools
# - installs runtime + dev dependencies

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

echo "Root: $ROOT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

echo "Upgrading pip, setuptools, wheel..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

echo "Installing requirements + dev tools..."
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt" black flake8 isort pytest

echo "Bootstrap complete. To activate the venv run:"
echo "  source $VENV_DIR/bin/activate"
echo "Then you can run e.g. python extract/egx/scraper.py --outdir extract/egx/raw"
