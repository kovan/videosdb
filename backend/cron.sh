#! /bin/sh
docker-compose run backend poetry run python manage.py videosdb --check-for-new-videos
