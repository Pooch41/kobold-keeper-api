#!/bin/sh


echo "Waiting for PostgreSQL database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done

echo "PostgreSQL started. Running migrations..."
python manage.py migrate --no-input

echo "Migrations complete. Collecting static files..."
python manage.py collectstatic --no-input

echo "Static files collected. Starting Gunicorn server..."


exec /usr/local/bin/gunicorn kobold_keeper.wsgi:application --bind 0.0.0.0:8000
