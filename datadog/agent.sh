#!/usr/bin/env bash
# Dedicated Datadog Agent container for the BitsTalk POV (Docker on the laptop, e.g. colima).
# The API key goes into a 0600 env file (.dd/datadog.env), never onto the docker command line.
# Usage: DD_API_KEY=... datadog/agent.sh up | down | status
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
NAME=bitstalk-pov-datadog-agent
ENV_FILE="$ROOT/.dd/datadog.env"

write_env_file() {
  (
    umask 077
    mkdir -p "$ROOT/.dd"
    cat > "$ENV_FILE" <<ENV
DD_API_KEY=${DD_API_KEY}
DD_SITE=${DD_SITE:-datadoghq.com}
DD_ENV=${DD_ENV:-pov}
DD_HOSTNAME=${DD_HOSTNAME:-leendert-meyer-bitstalk-pov}
DD_TAGS=customer:bitstalk project:agent-o11y-pov
DD_APM_ENABLED=true
DD_APM_NON_LOCAL_TRAFFIC=true
DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
DD_LOGS_ENABLED=true
DD_LOGS_CONFIG_AUTO_MULTI_LINE_DETECTION=true
DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=false
DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED=false
ENV
  )
  chmod 600 "$ENV_FILE"
}

case "${1:-up}" in
  up)
    : "${DD_API_KEY:?DD_API_KEY must be set}"
    write_env_file
    if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
      echo "Datadog Agent already running ($NAME)"
      exit 0
    fi
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" --restart unless-stopped \
      --cgroupns host --pid host \
      --env-file "$ENV_FILE" \
      -p 127.0.0.1:8126:8126/tcp \
      -p 127.0.0.1:8125:8125/udp \
      -v /var/run/docker.sock:/var/run/docker.sock:ro \
      -v /proc/:/host/proc/:ro \
      -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
      -v "$ROOT/backend/logs:/var/log/bitstalk-chatbot:ro" \
      -v "$DIR/conf.d/bitstalk-chatbot.d:/conf.d/bitstalk-chatbot.d:ro" \
      registry.datadoghq.com/agent:7 >/dev/null
    echo "Datadog Agent started ($NAME)"
    ;;
  down)
    docker rm -f "$NAME" >/dev/null 2>&1 && echo "Datadog Agent stopped" || echo "Datadog Agent not running"
    ;;
  status)
    docker exec "$NAME" agent status
    ;;
  *)
    echo "Usage: $0 up|down|status" >&2
    exit 1
    ;;
esac
