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
- **Log streams**: SSE broadcaster + **persistent `deployment_events` table** (survives restarts)

## Deployment events

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/deployments/{id}/events` | Full persisted event log |
| `GET /api/v1/deployments/{id}/timeline` | Step durations + correlation ID |
| `GET /api/v1/logs/{id}/stream?token=` | Live SSE with DB replay + `Last-Event-ID` |

Run migrations: `alembic upgrade head` (through revision `006`).

## Structured logging

- `StructuredLoggingMiddleware` binds `request_id`, `method`, `path`, and `deployment_id` (when present in URL)
- Provision workers bind `deployment_id` via `bind_deployment_context()`
- `GET /metrics` — in-process counters and request duration histogram

## Provision jobs (Phase 5)

| Table | Purpose |
|-------|---------|
| `provision_jobs` | Durable queue: `pending` → `running` → `completed` / `failed` |

Each deploy/resume enqueues a job; the background task executes it immediately. The scheduler also runs `process_pending_jobs()` for stuck `pending` rows.

## Incidents & audit (Phase 11)

| Table | Purpose |
|-------|---------|
| `audit_events` | Immutable structured audit trail (dual-written with `audit_logs`) |
| `incident_events` | Auto-opened on provision failure; resolve via API |

| Endpoint | Action |
|----------|--------|
| `GET /api/v1/incidents` | List your incidents |
| `POST /api/v1/incidents/{id}/resolve` | Mark resolved |
| `GET /api/v1/ops/analytics` | Scan grades, alert history, retry stats |

## Provisioning recovery (Phase 2)

| State | Meaning |
|-------|---------|
| `QUEUED` → `CREATING_SERVER` → `WAITING_FOR_SSH` → `HARDENING` → `INSTALLING_DOCKER` → `INSTALLING_OPENCLAW` → `VERIFYING` → `COMPLETED` | Happy path |
| `FAILED` / `ROLLING_BACK` / `ROLLED_BACK` | Terminal / cleanup |

| Endpoint | Action |
|----------|--------|
| `POST /api/v1/deployments/{id}/resume` | Idempotent resume from last state |
| `POST /api/v1/deployments/{id}/rollback` | Delete cloud server + `ROLLED_BACK` |

Stuck deployments (>2h in active state) are marked `FAILED` by the hourly worker (`recover_orphaned_resources`).

## Failure modes

| Symptom | Action |
|---------|--------|
| Deploy stuck in `provisioning` | Check provider token + API status |
| SSE disconnects | Client auto-reconnects (5 retries); check Railway timeout |
| Alerts not firing | Verify `enabled` alerts + cooldown + Resend key |

## Scaling notes

Single Railway instance is sufficient for MVP. Scale horizontally only after moving SSE to shared pub/sub (out of scope for lean MVP).
