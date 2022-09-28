#!/bin/bash
pgrep docker || sudo service docker start

if [[ -z "$BRANCH_NAME" ]]
then
    export REPO=grc.io/$PROJECT_NAME/$BRANCH_NAME/
    docker-compose pull
fi

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

