#!/usr/bin/env bash
# Entrypoint script for the Django Web service on Render

set -o errexit  # exit immediately on errors
set -o pipefail # catch errors in pipelines
set -o nounset  # treat unset variables as errors


echo "Starting Kobold Keeper Web Service (Django)"


if [ -n "${DATABASE_URL:-}" ]; then
  echo "⏳ Waiting for the PostgreSQL database to become available..."
  MAX_RETRIES=30
  RETRY_INTERVAL=2
  for ((i=1; i<=MAX_RETRIES; i++)); do
    if python -c "import psycopg2; from urllib.parse import urlparse; \
      u=urlparse('${DATABASE_URL}'); \
      psycopg2.connect(dbname=u.path[1:], user=u.username, password=u.password, host=u.hostname, port=u.port).close()" 2>/dev/null; then
      echo "✅ Database is ready!"
      break
    fi
    echo "⏱ Attempt $i/$MAX_RETRIES: Database not ready yet..."
    sleep $RETRY_INTERVAL
  done
else
  echo "⚠️ DATABASE_URL not set — skipping readiness check."
fi

# 2. Apply database migrations
echo "🛠 Applying Django database migrations..."
python manage.py migrate --noinput

# 3. Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# 5. Start Gunicorn web server
echo "🚀 Launching Gunicorn on port ${PORT:-8000}..."
exec gunicorn kobold_keeper.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers 4 \
  --timeout 90 \
  --log-level info \
  --access-logfile '-' \
  --error-logfile '-'
