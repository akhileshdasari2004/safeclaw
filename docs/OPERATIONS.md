# SafeClaw Operations

## Health endpoints

| Path | Purpose |
|------|---------|
| `GET /health` | Liveness |
| `GET /live` | Process alive |
| `GET /ready` | Database connectivity |

## Observability

- Structured JSON logs in production (`APP_ENV=production`)
- `X-Request-ID` on every response
- Deployment correlation via `deployment_id` in SSE log events
- Audit log table for auth/billing/deploy actions

## Background jobs

- **Cost alerts**: APScheduler interval job (`ALERTS_POLL_INTERVAL_SECONDS`, default 3600)
- **Log streams**: In-memory SSE broadcaster with TTL cleanup (no Redis)

## Failure modes

| Symptom | Action |
|---------|--------|
| Deploy stuck in `provisioning` | Check provider token + API status |
| SSE disconnects | Client auto-reconnects (5 retries); check Railway timeout |
| Alerts not firing | Verify `enabled` alerts + cooldown + Resend key |

## Scaling notes

Single Railway instance is sufficient for MVP. Scale horizontally only after moving SSE to shared pub/sub (out of scope for lean MVP).
