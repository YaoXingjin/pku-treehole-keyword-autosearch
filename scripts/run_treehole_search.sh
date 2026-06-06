#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/pku-treehole-keyword-autosearch}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
STATE_DIR="${STATE_DIR:-$PROJECT_DIR/state}"

cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR" "$STATE_DIR"

if [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
  :
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python || true)"
fi

if [[ -z "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
  echo "Python interpreter not found."
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/config_private.py" ]]; then
  echo "Missing config_private.py. Upload it manually and set permission to 600."
  exit 1
fi

export TREEHOLE_STATE_FILE="${TREEHOLE_STATE_FILE:-$STATE_DIR/seen_posts_state.json}"
export PYTHONUNBUFFERED=1

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') gateway login ====="
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
    "$PYTHON_BIN" "$PROJECT_DIR/scripts/its_network_login.py"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') treehole search ====="
} >> "$LOG_DIR/treehole-search.log" 2>&1

"$PYTHON_BIN" "$PROJECT_DIR/search_keyword.py" --non-interactive >> "$LOG_DIR/treehole-search.log" 2>&1
