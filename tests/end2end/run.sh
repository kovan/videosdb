#!/bin/sh
pgrep docker || sudo service docker start

rm -fr ./dist

docker compose up --build --detach \
&& \
until  nc -z localhost 8080; do sleep 1; done \
&& \
docker compose run --rm backend -c -e \
&& \
docker compose run frontend generate-and-start\

docker compose down
