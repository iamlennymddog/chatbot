#!/usr/bin/env bash
# Starts the BitsTalk Deal Buddy backend (:3001) and frontend (:5173).
# Usage: ANTHROPIC_API_KEY=sk-ant-... ./start.sh   (or export it first)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

export ANTHROPIC_API_KEY=`getSecretKey BITSTALK_ANTHROPIC_KEY`
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set. Run: export ANTHROPIC_API_KEY=sk-ant-..." >&2
  exit 1
fi
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-sonnet-5-5}"     # orchestrator (Deal Buddy)
export SPECIALIST_MODEL="${SPECIALIST_MODEL:-claude-haiku-5-5}"    # sub-agent (Deals Specialist)

for dir in backend frontend; do
  [[ -d "$ROOT/$dir/node_modules" ]] || (cd "$ROOT/$dir" && npm install)
done

cleanup() {
  echo "Stopping..."
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

(cd "$ROOT/backend" && exec node src/server.js) &
BACKEND_PID=$!

(cd "$ROOT/frontend" && exec npx vite --port 5173) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:3001  (logs: backend/logs/app.log)"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."
# Exit (and stop both) as soon as either process dies. bash 3.2 on macOS has no `wait -n`.
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
