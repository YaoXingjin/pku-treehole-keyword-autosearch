#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/pku-treehole-keyword-autosearch}"

cd "$PROJECT_DIR"

if [[ ! -f requirements.txt ]]; then
  echo "Missing requirements.txt"
  exit 1
fi

if [[ ! -f search_keyword.py ]]; then
  echo "Missing search_keyword.py"
  exit 1
fi

if [[ ! -f config_private.py ]]; then
  echo "Missing config_private.py"
  exit 1
fi

mode="$(stat -c '%a' config_private.py)"
if [[ "$mode" != "600" ]]; then
  echo "config_private.py permission is $mode; run: chmod 600 config_private.py"
  exit 1
fi

if [[ -x .venv/bin/python ]] && .venv/bin/python -c "import requests" >/dev/null 2>&1; then
  .venv/bin/python -m py_compile client.py meow_push.py search_keyword.py
else
  python3 -m py_compile client.py meow_push.py search_keyword.py
fi

echo "Deploy readiness check passed."
