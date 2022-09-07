#!/bin/sh
sudo service docker start



docker compose up --build --detach \
&& \
sleep 1 \
&& \
docker compose run --rm \
    backend \
        --check-for-new-videos \
        --exclude-transcripts \
&& \
docker compose run \
    frontend \
    yarn generate \
&& \
docker compose run frontend yarn start

docker compose down
