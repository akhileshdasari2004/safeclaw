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

## SSH key rotation (deployed servers)

After a deploy reaches `completed`, rotate keys without reprovisioning:

```http
POST /api/v1/deployments/{id}/rotate-ssh
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_public_key": "ssh-rsa AAAA... user@host",
  "new_private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
}
```

- Updates encrypted private key at rest and `ssh_key_version` on the deployment
- Appends the new public key to `/home/safeclaw/.ssh/authorized_keys` over SSH
- Emits a `ssh_rotation` deployment event and `deployment.ssh_rotated` audit event
- **Operational note:** generate a new keypair offline; keep the old key until you confirm login with the new key

## Secret rotation

| Secret | Rotation cadence |
|--------|------------------|
| JWT_SECRET | 90 days (invalidates sessions) |
| ENCRYPTION_KEY | Requires re-encrypting stored SSH keys |
| Stripe webhook secret | On endpoint rotation |
| Hetzner / DO tokens | 90 days or on leak |
| Deployment SSH keys | On compromise or quarterly via `rotate-ssh` |

## Webhook validation

All license issuance flows through `checkout.session.completed` with `stripe.Webhook.construct_event`.

## JWT

Access tokens expire per `JWT_ACCESS_EXPIRE_MINUTES`. Refresh tokens for session extension.
