#!/bin/bash
export PATH="$HOME/.poetry/bin:$PATH"
poetry run python manage.py migrate --noinput
exec poetry run gunicorn --bind 0.0.0.0:8000 --workers=$(expr $(cat /proc/cpuinfo | grep ^processor | wc -l) \* 2 + 1) --log-level=info --log-file=- project.wsgi
