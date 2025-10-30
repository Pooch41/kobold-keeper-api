#!/bin/sh

# 1. Wait for database readiness using netcat (nc).
echo "Waiting for PostgreSQL database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done

echo "PostgreSQL started. Running migrations..."
# 2. Run Django database migrations.
python manage.py migrate --no-input

echo "Migrations complete. Collecting static files..."
# 3. Collect static files for Gunicorn to serve.
python manage.py collectstatic --no-input

echo "Static files collected. Starting Gunicorn server..."

# 4. Start the Gunicorn server, binding to all interfaces on port 8000.
exec /usr/local/bin/gunicorn kobold_keeper.wsgi:application --bind 0.0.0.0:8000
