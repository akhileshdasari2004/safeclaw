#!/usr/bin/env bash
# SafeClaw server hardening — Ubuntu 22.04 LTS
# Executed remotely via SSH during provisioning. Idempotent where possible.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
SAFECLAW_USER="${SAFECLAW_USER:-safeclaw}"
SSH_PORT="${SSH_PORT:-22}"

echo "[safeclaw] Starting hardening on $(lsb_release -ds 2>/dev/null || echo unknown)"

# --- System updates ---
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq ufw fail2ban unattended-upgrades apt-listchanges curl ca-certificates gnupg lsb-release

# --- Non-root deploy user ---
if ! id -u "$SAFECLAW_USER" &>/dev/null; then
  useradd -m -s /bin/bash -G sudo,docker "$SAFECLAW_USER" 2>/dev/null || useradd -m -s /bin/bash -G sudo "$SAFECLAW_USER"
  mkdir -p "/home/$SAFECLAW_USER/.ssh"
  chmod 700 "/home/$SAFECLAW_USER/.ssh"
  if [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys "/home/$SAFECLAW_USER/.ssh/authorized_keys"
    chown -R "$SAFECLAW_USER:$SAFECLAW_USER" "/home/$SAFECLAW_USER/.ssh"
    chmod 600 "/home/$SAFECLAW_USER/.ssh/authorized_keys"
  fi
  echo "$SAFECLAW_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$SAFECLAW_USER"
  chmod 440 "/etc/sudoers.d/$SAFECLAW_USER"
fi

# --- SSH hardening (preserve key auth; do not brick access) ---
SSHD_CONFIG=/etc/ssh/sshd_config.d/99-safeclaw.conf
cat > "$SSHD_CONFIG" <<EOF
PermitRootLogin prohibit-password
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
# Keep port 22 unless explicitly changed — changing port can lock users out
systemctl reload sshd || systemctl reload ssh

# --- UFW ---
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "$SSH_PORT"/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 18789/tcp comment 'OpenClaw' || true
ufw --force enable

# --- fail2ban ---
cat > /etc/fail2ban/jail.local <<'JAIL'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
JAIL
systemctl enable fail2ban
systemctl restart fail2ban

# --- Unattended upgrades ---
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'UPG'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
UPG

# --- Sysctl hardening ---
cat > /etc/sysctl.d/99-safeclaw.conf <<'SYS'
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.tcp_syncookies = 1
SYS
sysctl --system >/dev/null 2>&1 || true

echo "[safeclaw] Hardening complete"
