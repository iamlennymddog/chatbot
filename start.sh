#!/usr/bin/env bash
# Starts BitsTalk Deal Buddy: Datadog Agent (docker), backend (:3001, dd-trace) and frontend (:5173).
# Usage: ./start.sh   (ANTHROPIC_API_KEY and DD_API_KEY are read with getSecretKey)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

export ANTHROPIC_API_KEY=`getSecretKey BITSTALK_ANTHROPIC_KEY`
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set. Run: export ANTHROPIC_API_KEY=sk-ant-..." >&2
  exit 1
fi
export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-sonnet-5-5}"     # orchestrator (Deal Buddy)
export SPECIALIST_MODEL="${SPECIALIST_MODEL:-claude-haiku-5-5}"    # sub-agent (Deals Specialist)

# Datadog API key: only the Agent container gets it (via a 0600 env file), not the app.
DD_API_KEY="${DD_API_KEY:-`getSecretKey BITSTALK_DD_API_KEY`}"

# Unified service tagging
export DD_SERVICE="${DD_SERVICE:-bitstalk-deals-chatbot-api}"
export DD_ENV="${DD_ENV:-pov}"
export DD_VERSION="${DD_VERSION:-1.0.0}"
export DD_SITE="${DD_SITE:-datadoghq.com}"

for dir in backend frontend; do
  [[ -d "$ROOT/$dir/node_modules" ]] || (cd "$ROOT/$dir" && npm install)
done
mkdir -p "$ROOT/backend/logs"

BACKEND_CMD=(node src/server.js)
if [[ -n "${DD_API_KEY:-}" ]]; then
  echo "Starting Datadog Agent container..."
  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running (try: colima start)." >&2
    exit 1
  fi
  DD_API_KEY="$DD_API_KEY" "$ROOT/datadog/agent.sh" up
  for _ in $(seq 1 30); do
    curl -sf http://localhost:8126/info >/dev/null && break
    sleep 1
  done
  curl -sf http://localhost:8126/info >/dev/null || { echo "ERROR: Datadog Agent not reachable on :8126" >&2; exit 1; }

  # APM + log/trace correlation + runtime metrics via dd-trace -> local Agent
  export DD_TRACE_AGENT_URL="http://localhost:8126"
  export DD_DOGSTATSD_HOST="localhost"
  export DD_LOGS_INJECTION=true
  export DD_RUNTIME_METRICS_ENABLED=true
  # dd-trace's own LLM Obs stays OFF: agent spans come from OpenTelemetry (below) so the
  # Execution Graph gets span links, which dd-trace JS cannot emit.
  unset DD_LLMOBS_ENABLED

  # LLM Observability via OpenTelemetry GenAI -> Datadog OTLP intake (service.name = ml_app)
  export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:-https://otlp.${DD_SITE}/v1/traces}"
  export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL="http/protobuf"
  export OTEL_EXPORTER_OTLP_TRACES_HEADERS="dd-api-key=${DD_API_KEY},dd-otlp-source=llmobs,DD-LLMObs-Enabled=true"
  export OTEL_SERVICE_NAME="${DD_LLMOBS_ML_APP:-bitstalk-deal-buddy}"
  BACKEND_CMD=(node --import dd-trace/initialize.mjs src/server.js)
else
  echo "WARNING: DD_API_KEY not set - running WITHOUT Datadog instrumentation."
fi
unset DD_API_KEY

cleanup() {
  echo "Stopping app (Datadog Agent keeps running; stop it with: datadog/agent.sh down)..."
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

(cd "$ROOT/backend" && exec "${BACKEND_CMD[@]}") &
BACKEND_PID=$!

(cd "$ROOT/frontend" && exec npx vite --port 5173) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:3001  (logs: backend/logs/app.log)"
echo "Frontend: http://localhost:5173"
[[ -n "${OTEL_SERVICE_NAME:-}" ]] && echo "Datadog:  https://app.${DD_SITE}/llm/traces?query=%40ml_app%3A${OTEL_SERVICE_NAME}"
echo "Press Ctrl+C to stop."
# Exit (and stop both) as soon as either process dies. bash 3.2 on macOS has no `wait -n`.
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
