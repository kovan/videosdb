#!/bin/bash

POETRY=/home/pi/.local/bin/poetry

cd /home/pi/prj/videosdb
docker exec videosdb_backend-sadhguru_1 nice -n 20 poetry run python manage.py videosdb --check-for-new-videos

cd /home/pi/prj/videosdb/backend
nice -n 20 $POETRY run python -O manage.py videosdb --download-and-register-in-ipfs --settings=project.settings-fileserver

