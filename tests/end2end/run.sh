#!/bin/sh
sudo service docker start



docker compose build \
&& \
docker compose up --detach \
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
docker cp end2end-frontend-1:/src/dist dist

docker compose down
