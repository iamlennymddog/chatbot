#!/usr/bin/env bash
# Stops BitsTalk Deal Buddy: backend (:3001), frontend (:5173) and the Datadog Agent container.
# Usage: ./stop.sh               stop everything
#        ./stop.sh --keep-agent  stop the app, leave the Datadog Agent running
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
KEEP_AGENT=0
[[ "${1:-}" == "--keep-agent" ]] && KEEP_AGENT=1

# Sends SIGTERM to whatever listens on the port (the backend flushes pending OTel spans on SIGTERM), waits up to 5s, then SIGKILLs.
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

if [[ "$KEEP_AGENT" == 1 ]]; then
  echo "Datadog Agent: left running (stop it later with ./stop.sh or datadog/agent.sh down)"
elif docker info >/dev/null 2>&1; then
  printf 'Datadog Agent: '
  "$ROOT/datadog/agent.sh" down
else
  echo "Datadog Agent: Docker is not running, nothing to stop"
fi
