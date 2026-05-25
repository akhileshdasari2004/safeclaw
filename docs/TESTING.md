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
- Health / readiness
- Deployment log broadcaster
- SSE endpoint auth
- Provider catalog mocks

### Mocks

`tests/mocks/providers.py` — use `MockProvider` to patch `get_provider` in provisioning tests.

## Frontend

```bash
npm run test -w @safeclaw/frontend
npm run lint -w @safeclaw/frontend
npm run build -w @safeclaw/frontend
```

## CI

GitHub Actions runs backend pytest + frontend lint/test/build on push to `main`.
