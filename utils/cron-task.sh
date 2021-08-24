#!/bin/bash

POETRY=/home/pi/.local/bin/poetry
DOCKER_COMPOSE=/home/pi/.local/bin/docker-compose
cd /home/pi/prj/videosdb
nice -n 20 $DOCKER_COMPOSE run --rm backend-sadhguru nice -n 20 poetry run python manage.py videosdb --check-for-new-videos
cd /home/pi/prj/videosdb/backend
nice -n 20 $POETRY run python -O manage.py videosdb --download-and-register-in-ipfs --settings=project.settings-fileserver

