#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PACKAGE_NAME="codex-workspaces"

usage() {
  cat <<'EOF'
Usage:
  ./local_install.sh              Install editable dev mode, best for local testing
  ./local_install.sh --reinstall  Reinstall editable mode with --force-reinstall
  ./local_install.sh --wheel      Build wheel and force reinstall it
  ./local_install.sh --uninstall  Uninstall codex-workspaces from this Python env
  ./local_install.sh --clean      Remove local build artifacts

Env:
  PYTHON_BIN=python3.11 ./local_install.sh
EOF
}

clean_artifacts() {
  rm -rf build dist src/codex_workspaces.egg-info
}

show_result() {
  echo
  echo "Python: $("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"
  echo "pip package:"
  "$PYTHON_BIN" -m pip show "$PACKAGE_NAME" || true
  echo
  if command -v codex-workspaces >/dev/null 2>&1; then
    echo "CLI: $(command -v codex-workspaces)"
    codex-workspaces help >/dev/null
    echo "CLI check: ok"
  else
    echo "CLI not found on PATH. Check your Python scripts directory."
  fi
}

mode="${1:---editable}"
case "$mode" in
  --editable)
    "$PYTHON_BIN" -m pip install -e ".[dev]"
    show_result
    ;;
  --reinstall)
    "$PYTHON_BIN" -m pip install --force-reinstall -e ".[dev]"
    show_result
    ;;
  --wheel)
    clean_artifacts
    "$PYTHON_BIN" -m pip install build twine
    "$PYTHON_BIN" -m build
    "$PYTHON_BIN" -m pip install --force-reinstall dist/codex_workspaces-*.whl
    show_result
    ;;
  --uninstall)
    "$PYTHON_BIN" -m pip uninstall -y "$PACKAGE_NAME"
    ;;
  --clean)
    clean_artifacts
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown option: $mode" >&2
    usage >&2
    exit 2
    ;;
esac
