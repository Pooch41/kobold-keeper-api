#!/usr/bin/env bash

# This script is the dedicated entrypoint for the Render Web Service.

# 1. Wait for database readiness (a safety measure)
echo "Waiting 5 seconds for services to initialize..."
sleep 5

# 2. Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# 3. Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 4. Start Gunicorn server
# $PORT is an environment variable automatically provided by Render
echo "Starting Gunicorn server on port $PORT..."
exec gunicorn kobold_keeper.wsgi:application --bind 0.0.0.0:$PORT --workers 4
