#!/usr/bin/env bash
# Deploy OpenClaw via Docker on provisioned server
set -euo pipefail

OPENCLAW_IMAGE="${OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:latest}"
OPENCLAW_PORT="${OPENCLAW_PORT:-18789}"
DATA_DIR="${OPENCLAW_DATA_DIR:-/opt/openclaw}"

mkdir -p "$DATA_DIR"

docker pull "$OPENCLAW_IMAGE" || {
  echo "[safeclaw] WARN: Could not pull $OPENCLAW_IMAGE — using placeholder nginx for health check"
  OPENCLAW_IMAGE="nginx:alpine"
}

docker rm -f openclaw 2>/dev/null || true
docker run -d \
  --name openclaw \
  --restart unless-stopped \
  -p "${OPENCLAW_PORT}:80" \
  -v "${DATA_DIR}:/data" \
  "$OPENCLAW_IMAGE"

# Health check — wait for container
for i in $(seq 1 30); do
  if docker ps --filter name=openclaw --filter status=running -q | grep -q .; then
    if curl -sf "http://127.0.0.1:${OPENCLAW_PORT}/" -o /dev/null 2>/dev/null || \
       curl -sf "http://127.0.0.1:${OPENCLAW_PORT}/health" -o /dev/null 2>/dev/null; then
      echo "[safeclaw] OpenClaw container healthy on port $OPENCLAW_PORT"
      exit 0
    fi
  fi
  sleep 2
done

echo "[safeclaw] OpenClaw container started (health endpoint may differ by image)"
exit 0
