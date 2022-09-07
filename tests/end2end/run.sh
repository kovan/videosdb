#!/bin/sh
sudo service docker start

rm -fr ./dist

docker compose up --build --detach \
&& \
sleep 1 \
&& \
docker compose run --rm backend -c -e \
&& \
docker compose run frontend yarn generate-and-run \

docker compose down
