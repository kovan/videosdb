#! /bin/sh
docker-compose run backend poetry run python manage.py --check-for-new-videos
