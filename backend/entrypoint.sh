#!/bin/sh
set -e

if [ "$1" = "gunicorn" ]; then
  alembic upgrade head
  python scripts/seed_demo.py
fi

exec "$@"
