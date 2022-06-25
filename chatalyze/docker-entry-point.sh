#!/bin/bash

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Make database migrations
echo "Make database migrations"
python manage.py makemigrations
python manage.py makemigrations dashboard

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Start server
echo "Starting server"
gunicorn --bind 0.0.0.0:8080 core.wsgi
