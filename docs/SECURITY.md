# SafeClaw Security

## SSH hardening checklist (provisioned servers)

- [ ] UFW enabled (deny incoming default)
- [ ] fail2ban active for sshd
- [ ] `PermitRootLogin prohibit-password`
- [ ] `PasswordAuthentication no`
- [ ] Non-root `safeclaw` user with sudo
- [ ] Unattended security upgrades
- [ ] Sysctl hardening applied
- [ ] Only required ports open (22, 80, 443, OpenClaw)

## Application checklist

- [ ] `JWT_SECRET` ≥ 32 random bytes
- [ ] `ENCRYPTION_KEY` Fernet key for SSH private keys at rest
- [ ] Stripe webhook signature verification enabled
- [ ] CORS limited to production frontend origin
- [ ] Rate limiting configured (`RATE_LIMIT_PER_MINUTE`)
- [ ] No secrets in frontend bundle
- [ ] Provider tokens scoped (project-level, server CRUD only)
- [ ] SSE log endpoint requires JWT query param over HTTPS only

## Secret rotation

| Secret | Rotation cadence |
|--------|------------------|
| JWT_SECRET | 90 days (invalidates sessions) |
| ENCRYPTION_KEY | Requires re-encrypting stored SSH keys |
| Stripe webhook secret | On endpoint rotation |
| Hetzner / DO tokens | 90 days or on leak |

## Webhook validation

All license issuance flows through `checkout.session.completed` with `stripe.Webhook.construct_event`.

## JWT

Access tokens expire per `JWT_ACCESS_EXPIRE_MINUTES`. Refresh tokens for session extension.
