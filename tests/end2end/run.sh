#!/bin/sh
pgrep docker || sudo service docker start



rm -fr ./dist

docker compose build \
&& \
docker compose up --detach --remove-orphans \
&& \
docker compose run  --rm -e LOGLEVEL=TRACE backend -m unittest \
&& \
docker compose run  -e LOGLEVEL=DEBUG --rm backend -O -m videosdb -c -e \
&& \
docker compose run frontend yarn generate-and-start\


#docker compose down

