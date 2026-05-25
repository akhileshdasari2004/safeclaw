# SafeClaw

Production-ready SaaS to provision hardened VPS servers, install OpenClaw, run security scans, and monitor infrastructure costs.

## Architecture

```txt
/apps
  /frontend   — Next.js 14 (Vercel)
  /backend    — FastAPI (Railway)
/packages
  /shared-types
  /config
/infrastructure
  /docker
  /scripts    — SSH hardening & install scripts (Ubuntu 22.04)
/docs
```

**Assumptions (explicit):**

- OpenClaw image defaults to `ghcr.io/openclaw/openclaw:latest` — verify image name/tag for your environment; install script falls back to `nginx:alpine` if pull fails.
- Provisioning requires the SSH **private** key (encrypted at rest) to run remote hardening after VPS create.
- Hetzner uses official `hcloud` SDK; DigitalOcean uses documented REST API v2 via `httpx`.
- Stripe Checkout creates users/licenses on `checkout.session.completed` webhook only.

## Quick start (local)

```bash
cp .env.example .env
# Edit .env with secrets (JWT, encryption, optional Stripe/Resend/provider tokens)

make docker-up          # Postgres on :5432
make install            # Python venv + npm workspaces
make migrate            # Alembic
make seed               # dev@safeclaw.local / devpassword123 + license
make dev                # :3000 frontend + :8000 API
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Environment variables

See [.env.example](.env.example). Required for production:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Supabase Postgres (asyncpg URL) |
| `JWT_SECRET` | ≥32 chars |
| `ENCRYPTION_KEY` | SSH key encryption at rest |
| `STRIPE_*` | Checkout + webhooks |
| `RESEND_API_KEY` | License & alert emails |
| `HETZNER_API_TOKEN` / `DIGITALOCEAN_API_TOKEN` | Provisioning |

## Core flow

1. Marketing → Pricing → Stripe Checkout
2. Webhook → user + license + Resend email
3. Login → Deploy wizard → background provision
4. SSH harden → Docker → OpenClaw → dashboard status/logs
5. Security scan + cost alerts

## Commands

| Command | Description |
|---------|-------------|
| `make backend-test` | pytest |
| `make lint` | ruff + frontend lint |
| `make docker-down` | Stop local stack |

## Deployment

Full production steps: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Security

- JWT access tokens, webhook signature verification, rate limiting (SlowAPI)
- Secure headers, request IDs, audit logs
- No provider tokens in frontend
- SSH private keys encrypted with Fernet-derived key

## License

Proprietary — SafeClaw MVP.
