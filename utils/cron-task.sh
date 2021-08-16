#!/bin/bash

POETRY=/home/pi/.local/bin/poetry

cd /home/pi/prj/videosdb
nice -n 11 docker-compose run --rm backend-sadhguru nice -n 10 poetry run python manage.py videosdb --check-for-new-videos
nice -n 11 $POETRY run python -O manage.py videosdb --download-and-register-in-ipfs --settings=project.settings-fileserver