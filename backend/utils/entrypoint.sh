#!/bin/bash
export PATH="$HOME/.poetry/bin:$PATH"
poetry run python manage.py migrate --noinput
exec poetry run gunicorn --preload --bind 0.0.0.0:8000 --threads=100 --workers=$(cat /proc/cpuinfo | grep ^processor | wc -l) project.wsgi
