#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu VPS, before the first `docker compose
# up -d --build`. Idempotent -- safe to re-run (each step checks whether
# its own work is already done and skips if so).
#
# Usage (as a user with sudo, on the VPS itself):
#   curl -fsSL https://raw.githubusercontent.com/Wasim-Shaikh25/CaseMap/main/scripts/vps-bootstrap.sh | bash
# or, after `git clone`:
#   bash scripts/vps-bootstrap.sh
#
# What this does, in order:
#   1. Installs Docker Engine + the compose plugin (official apt repo).
#   2. Adds a 2GB swap file, if none exists. CaseMap's ML stack peaked
#      around 2.9GB RSS processing one document in local testing
#      (2026-09-11) -- on a 4GB VPS that leaves less headroom than ideal
#      once OS + Docker + Caddy overhead is counted. Swap is a cheap
#      safety net against an OOM-kill under a heavier document, not a
#      substitute for enough RAM in steady state.
#   3. Configures ufw: allow SSH (before enabling, so you don't lock
#      yourself out), allow 80/443 (Caddy), deny everything else. 8756
#      (casemap itself) is never opened here -- docker-compose.yml only
#      binds it to 127.0.0.1, not the public interface, so there is
#      nothing on it to block.
set -euo pipefail

echo "[1/3] Docker Engine + compose plugin..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "  already installed, skipping."
else
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "  installed. Log out and back in (or run 'newgrp docker') for the"
    echo "  group change to take effect without sudo."
fi

echo "[2/3] 2GB swap file..."
if swapon --show | grep -q . || [ -f /swapfile ]; then
    echo "  swap already present, skipping."
else
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    # Persist across reboots.
    if ! grep -q '^/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    fi
    echo "  created and enabled."
fi

echo "[3/3] ufw firewall (22, 80, 443)..."
if command -v ufw >/dev/null 2>&1; then
    sudo ufw allow OpenSSH
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    sudo ufw status verbose
else
    echo "  ufw not installed -- skipping (install it first if you want a firewall)."
fi

echo
echo "Done. Next steps if this is a first-time deploy:"
echo "  git clone https://github.com/Wasim-Shaikh25/CaseMap.git /opt/casemap"
echo "  cd /opt/casemap"
echo "  # edit Caddyfile: swap 'your-domain.example' for your real domain/IP"
echo "  docker compose up -d --build"
