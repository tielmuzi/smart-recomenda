#!/bin/sh
set -eu

mkdir -p /app/data
chown -R appuser:appuser /app/data

export APP_PORT="${PORT:-${APP_PORT:-8000}}"
exec su -s /bin/sh appuser -c 'exec python -m uvicorn backend.app.main:app --host "${APP_HOST:-0.0.0.0}" --port "$APP_PORT"'
