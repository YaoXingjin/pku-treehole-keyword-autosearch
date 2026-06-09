#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/pku-treehole-keyword-autosearch}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
STATE_DIR="${STATE_DIR:-$PROJECT_DIR/state}"
MEOW_BASE_URL="${MEOW_BASE_URL:-https://api.chuckfang.com}"
MEOW_DIRECT_FALLBACK="${MEOW_DIRECT_FALLBACK:-1}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

find_python_with_requests() {
  local candidate

  if [[ -x "$PYTHON_BIN" ]] && "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
    echo "$PYTHON_BIN"
    return 0
  fi

  candidate="$(command -v python3 || true)"
  if [[ -n "$candidate" ]] && "$candidate" -c "import requests" >/dev/null 2>&1; then
    echo "$candidate"
    return 0
  fi

  candidate="$(command -v python || true)"
  if [[ -n "$candidate" ]] && "$candidate" -c "import requests" >/dev/null 2>&1; then
    echo "$candidate"
    return 0
  fi

  return 1
}

notify_failure_with_python() {
  local python_bin="$1"
  local title="$2"
  local message="$3"

  if [[ -d "$PROJECT_DIR" ]]; then
    cd "$PROJECT_DIR"
  fi

  "$python_bin" - "$title" "$message" "$MEOW_BASE_URL" "$MEOW_DIRECT_FALLBACK" <<'PY'
import os
import sys

from meow_push import send_meow_push

title, message, base_url, direct_fallback = sys.argv[1:5]
nickname = os.getenv("MEOW_NICKNAME")

if not nickname:
    try:
        from config_private import MEOW_NICKNAME as nickname
    except Exception:
        nickname = ""

if not nickname or nickname.startswith("<"):
    raise SystemExit("MEOW_NICKNAME is not configured; cannot send failure notification.")

send_meow_push(
    nickname=nickname,
    title=title,
    msg=message,
    base_url=base_url,
    direct_fallback=direct_fallback.strip().lower() not in ("0", "false", "no", "off"),
)
PY
}

json_escape_for_curl() {
  sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n'
}

notify_failure_with_curl() {
  local title="$1"
  local message="$2"
  local nickname="${MEOW_NICKNAME:-}"
  local escaped_title
  local escaped_message

  if [[ -z "$nickname" ]] || [[ "$nickname" == \<* ]] || [[ "$nickname" == *"/"* ]]; then
    return 1
  fi

  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi

  escaped_title="$(printf '%s' "$title" | json_escape_for_curl)"
  escaped_message="$(printf '%s' "$message" | json_escape_for_curl)"

  curl -fsS \
    -H "Content-Type: application/json" \
    -X POST \
    "${MEOW_BASE_URL%/}/$nickname?msgType=text" \
    -d "{\"title\":\"$escaped_title\",\"msg\":\"$escaped_message\"}" \
    >/dev/null
}

notify_meow() {
  local title="$1"
  local message="$2"
  local label="$3"
  local notify_python

  if [[ "${MEOW_ENABLED:-1}" =~ ^(0|false|False|FALSE|no|No|NO|off|Off|OFF)$ ]]; then
    log "MeoW disabled; skip notification: $label"
    return 0
  fi

  notify_python="$(find_python_with_requests || true)"
  if [[ -n "$notify_python" ]] && notify_failure_with_python "$notify_python" "$title" "$message"; then
    log "MeoW notification sent: $label"
    return 0
  fi

  if notify_failure_with_curl "$title" "$message"; then
    log "MeoW notification sent with curl: $label"
    return 0
  fi

  log "Failed to send MeoW notification: $label"
}

notify_failure() {
  local reason="$1"
  local detail="$2"
  local title="树洞定时任务失败"
  local message

  message="$(
    cat <<EOF
失败原因：$reason
发生时间：$(date '+%Y-%m-%d %H:%M:%S %Z')
主机：$(hostname 2>/dev/null || echo unknown)
项目目录：$PROJECT_DIR

$detail

请登录云主机查看日志：
$LOG_FILE
EOF
  )"

  notify_meow "$title" "$message" "failure: $reason"
}

notify_startup() {
  local title="树洞定时任务启动"
  local message

  message="$(
    cat <<EOF
启动时间：$(date '+%Y-%m-%d %H:%M:%S %Z')
主机：$(hostname 2>/dev/null || echo unknown)
项目目录：$PROJECT_DIR
日志路径：$LOG_FILE

定时任务已开始执行，接下来会尝试登录北大网关并检索树洞。
EOF
  )"

  notify_meow "$title" "$message" "startup"
}

if [[ ! -d "$PROJECT_DIR" ]]; then
  LOG_FILE="${LOG_DIR:-$HOME/treehole-search.log}"
  notify_failure \
    "找不到项目目录" \
    "PROJECT_DIR 指向的目录不存在。请检查 ~/.config/pku-treehole-keyword-autosearch/env 中的 PROJECT_DIR。"
  exit 1
fi

cd "$PROJECT_DIR"
mkdir -p "$LOG_DIR" "$STATE_DIR"
LOG_FILE="$LOG_DIR/treehole-search.log"
log "===== scheduled run started =====" >> "$LOG_FILE"

if [[ "${MEOW_STARTUP_NOTIFY:-0}" =~ ^(1|true|True|TRUE|yes|Yes|YES|on|On|ON)$ ]]; then
  notify_startup >> "$LOG_FILE" 2>&1
else
  log "Startup notification disabled. Set MEOW_STARTUP_NOTIFY=1 to enable it." >> "$LOG_FILE"
fi

if ! PYTHON_BIN="$(find_python_with_requests)"; then
  log "Python interpreter with requests not found." >> "$LOG_FILE"
  notify_failure \
    "找不到可用 Python" \
    "没有找到可运行且已安装 requests 的 Python。请在项目目录执行：python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/config_private.py" ]]; then
  log "Missing config_private.py." >> "$LOG_FILE"
  notify_failure \
    "缺少 config_private.py" \
    "项目目录下没有 config_private.py。请手动上传该文件，并执行 chmod 600 config_private.py。若希望此类错误也能推送，请在 systemd 环境文件里设置 MEOW_NICKNAME。"
  exit 1
fi

export TREEHOLE_STATE_FILE="${TREEHOLE_STATE_FILE:-$STATE_DIR/seen_posts_state.json}"
export PYTHONUNBUFFERED=1

if ! {
  log "===== gateway login ====="
  env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u all_proxy \
    "$PYTHON_BIN" "$PROJECT_DIR/scripts/its_network_login.py"
  log "===== treehole search ====="
} >> "$LOG_FILE" 2>&1; then
  notify_failure \
    "北大网关登录失败" \
    "scripts/its_network_login.py 异常退出。可能是云主机尚未连通网关、账号密码错误、网关服务异常，或 MeoW/API 外网暂时不可达。"
  exit 1
fi

if ! "$PYTHON_BIN" "$PROJECT_DIR/search_keyword.py" --non-interactive >> "$LOG_FILE" 2>&1; then
  if tail -n 80 "$LOG_FILE" | grep -q "登录验证提醒已推送"; then
    log "Token verification notification was already sent by search_keyword.py." >> "$LOG_FILE"
    exit 1
  fi

  notify_failure \
    "树洞搜索脚本异常退出" \
    "search_keyword.py --non-interactive 运行失败。可能是树洞登录状态失效、令牌验证、搜索接口异常、配置错误或推送失败。"
  exit 1
fi
