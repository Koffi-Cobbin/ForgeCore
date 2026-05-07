#!/bin/bash
set -e

cd /home/runner/workspace/backend_platform

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server on 0.0.0.0:5000..."
gunicorn config.wsgi:application \
  --bind 0.0.0.0:5000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
