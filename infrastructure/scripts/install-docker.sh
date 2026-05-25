#!/usr/bin/env bash
# Install Docker CE on Ubuntu 22.04 — official Docker convenience script pattern
set -euo pipefail

if command -v docker &>/dev/null; then
  echo "[safeclaw] Docker already installed: $(docker --version)"
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

SAFECLAW_USER="${SAFECLAW_USER:-safeclaw}"
if id -u "$SAFECLAW_USER" &>/dev/null; then
  usermod -aG docker "$SAFECLAW_USER" || true
fi

echo "[safeclaw] Docker installed: $(docker --version)"
