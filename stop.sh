#!/usr/bin/env bash
# Stops BitsTalk Deal Buddy: backend (:3001) and frontend (:5173) started by ./start.sh.
# Usage: ./stop.sh
set -euo pipefail

# Sends SIGTERM to whatever listens on the port, waits up to 5s, then SIGKILLs.
stop_port() {
  local name="$1" port="$2" pids
  pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    echo "${name}: not running"
    return
  fi
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 10); do
    lsof -ti "tcp:${port}" -sTCP:LISTEN >/dev/null 2>&1 || { echo "${name}: stopped"; return; }
    sleep 0.5
  done
  kill -9 $(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null) 2>/dev/null || true
  echo "${name}: force-stopped"
}

stop_port "Backend  (:${PORT:-3001})" "${PORT:-3001}"
stop_port "Frontend (:5173)" 5173
