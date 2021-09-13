#!/bin/bash
export PATH="$HOME/.poetry/bin:$PATH"
poetry run python manage.py migrate --noinput
poetry run gunicorn --preload --bind 0.0.0.0:8000 project.wsgi