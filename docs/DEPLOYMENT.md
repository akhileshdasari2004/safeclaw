# SafeClaw Production Deployment Guide

## Production checklist

- [ ] Rotate `JWT_SECRET` and `ENCRYPTION_KEY` (use Fernet.generate_key() for encryption)
- [ ] Set `APP_ENV=production`
- [ ] Configure Supabase connection pooling (`?pgbouncer=true` if using pooler)
- [ ] Stripe live keys + webhook endpoint
- [ ] Resend verified domain
- [ ] Hetzner / DigitalOcean tokens (project-scoped, read/write for servers)
- [ ] CORS_ORIGINS = your Vercel URL only
- [ ] Disable default dev secrets

---

## Supabase (Postgres)

1. Create project at https://supabase.com
2. Copy **Connection string** (URI) from Settings → Database
3. Use async URL for backend:
   ```txt
   DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   DATABASE_URL_SYNC=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
   ```
4. Run migrations from CI or locally:
   ```bash
   cd apps/backend && alembic upgrade head
   ```

---

## Railway (Backend)

1. New project → Deploy from GitHub repo
2. Set root directory / Dockerfile: `infrastructure/docker/Dockerfile.backend`
3. Add environment variables from `.env.example`
4. Generate public domain → set `API_URL`
5. Health check path: `/health`
6. Stripe webhook URL: `https://<railway-domain>/api/v1/billing/webhook`

**Tradeoff:** Single FastAPI process runs alert polling in-process (simple, low cost). For scale, move polling to a Railway cron job or separate worker.

---

## Vercel (Frontend)

1. Import monorepo; set root to `apps/frontend` or use root with `vercel.json`
2. Environment:
   - `NEXT_PUBLIC_API_URL=https://<railway-api-domain>`
3. Build: `npm run build -w @safeclaw/frontend` from repo root
4. Set `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` to Vercel URLs in Railway env

---

## Stripe

1. Products → create Starter & Pro recurring prices
2. Set `STRIPE_PRICE_ID_STARTER`, `STRIPE_PRICE_ID_PRO`
3. Developers → Webhooks → Add endpoint:
   - URL: `https://<api>/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `invoice.payment_failed`, `customer.subscription.deleted`
4. Copy signing secret → `STRIPE_WEBHOOK_SECRET`

**Security:** Never trust client payment state; license issuance only via verified webhook.

---

## Hetzner Cloud

1. Console → Security → API Tokens → Read & Write
2. `HETZNER_API_TOKEN=`
3. Ensure Ubuntu 22.04 image available in chosen locations

---

## DigitalOcean

1. API → Tokens → Generate (write scope)
2. `DIGITALOCEAN_API_TOKEN=`

---

## Resend

1. Add domain + DNS records
2. `RESEND_API_KEY=`, `RESEND_FROM_EMAIL=SafeClaw <hello@yourdomain.com>`

---

## Cost estimation (MVP)

| Item | Est. monthly |
|------|----------------|
| Supabase Free/Pro | $0–25 |
| Railway API | $5–20 |
| Vercel Hobby/Pro | $0–20 |
| Hetzner CX22 per server | ~$6.49 each |
| DO Basic 2GB | ~$12 each |
| Stripe fees | 2.9% + $0.30 per charge |

Example: 10 customers × 1 CX22 server ≈ **$65/mo infra** + platform fees.

---

## Security checklist

- [ ] HTTPS everywhere
- [ ] Webhook signature validation enabled
- [ ] Rate limits tuned (`RATE_LIMIT_PER_MINUTE`)
- [ ] SSH keys only via encrypted storage
- [ ] Audit logs retained
- [ ] Provider tokens in secret manager only
- [ ] Idempotent deploy keys used in wizard
- [ ] fail2ban + UFW on all provisioned nodes

---

## OpenClaw image note

The install script pulls `OPENCLAW_IMAGE`. If the registry image differs in your environment, update env and verify health endpoint path. **TODO: verify provider SDK/image** for your OpenClaw release channel.
