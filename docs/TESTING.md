# SafeClaw Testing

## Backend

```bash
cd apps/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

### Coverage areas

- Auth register/login
- Health / readiness / metrics
- Deployment events, timeline, SSE replay
- Integration deployment pipeline (`tests/integration/deployment/`)
- Billing snapshots (`tests/billing/`)
- Job orchestrator + recovery
- Chaos failure re-exports (`tests/chaos/`)
- Multi-tenant authorization (`tests/test_authorization.py`)
- Provision jobs, incidents, SSH rotation, ops analytics
- Chaos suite (`tests/chaos/`)

### Mocks

- `tests/mocks/providers.py` — `MockProvider`, `TimeoutProvider`, `RateLimitProvider`
- `tests/mocks/ssh.py` — `MockSSHClient`, `set_ssh_config()` for failure injection

```bash
pytest -v --cov=app --cov-fail-under=55
```

## Frontend

```bash
npm run test -w @safeclaw/frontend
npm run lint -w @safeclaw/frontend
npm run build -w @safeclaw/frontend
```

## CI

GitHub Actions runs backend pytest + frontend lint/test/build on push to `main`.
