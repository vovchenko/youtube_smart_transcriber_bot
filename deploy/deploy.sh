#!/usr/bin/env bash
set -euo pipefail

# Load deploy config
if [ -f .env.deploy ]; then
    # shellcheck source=/dev/null
    source .env.deploy
fi

DROPLET_IP="${DROPLET_IP:?Set DROPLET_IP in .env.deploy or environment}"
DROPLET_USER="${DROPLET_USER:-root}"
REMOTE_DIR="/opt/youtube-smart-transcriber"

echo "==> Running lint checks..."
.venv/bin/ruff check .
.venv/bin/mypy --strict bot/
echo "==> Lint passed."

echo "==> Syncing to ${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}..."
rsync -azP --delete \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude 'data/' \
    --exclude '.git/' \
    --exclude 'tests/' \
    --exclude '.env' \
    --exclude '.env.deploy' \
    --exclude '.mypy_cache/' \
    --exclude '.ruff_cache/' \
    --exclude '.pytest_cache/' \
    ./ "${DROPLET_USER}@${DROPLET_IP}:${REMOTE_DIR}/"

echo "==> Installing dependencies and running migrations on remote..."
ssh "${DROPLET_USER}@${DROPLET_IP}" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/youtube-smart-transcriber

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m bot.db migrate

sudo systemctl daemon-reload
sudo systemctl restart youtube-smart-transcriber
REMOTE

echo "==> Tailing logs for 10 seconds..."
ssh "${DROPLET_USER}@${DROPLET_IP}" "journalctl -u youtube-smart-transcriber -f --no-pager" &
TAIL_PID=$!
sleep 10
kill "$TAIL_PID" 2>/dev/null || true

echo "==> Deploy complete."
