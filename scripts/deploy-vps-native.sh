#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVICE_NAME="openai-account-control.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script as root or through sudo." >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  cp .env.production.example .env
  echo "Created .env from .env.production.example." >&2
  echo "Edit .env on the VPS, set real secrets, then run this script again." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "python3-venv is required." >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m playwright install chromium

mkdir -p data data/evidence

if [ -d "frontend/dist" ]; then
  rm -rf backend/app/static
  mkdir -p backend/app/static
  cp -a frontend/dist/. backend/app/static/
elif [ ! -f "backend/app/static/index.html" ]; then
  echo "Frontend build is missing. Build frontend before deploying or upload backend/app/static." >&2
  exit 1
fi

install -m 0644 deploy/openai-account-control.service "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl --no-pager --full status "$SERVICE_NAME"
