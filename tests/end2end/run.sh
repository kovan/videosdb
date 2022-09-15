#!/bin/bash
pgrep docker || sudo service docker start

if [[ -z "${PROJECT_ID}" ]]; then
  compose_file="docker-compose.yml"
else # we are in Google CLoud Builder
  compose_file="docker-compose.cloudbuild.yml"
fi


rm -fr ./dist

docker compose -f $compose_file build -q \
&& \
docker compose -f $compose_file up --detach --remove-orphans \
&& \
until  nc -z localhost 8080; do sleep 1; done \
&& \
docker compose -f $compose_file run  --rm backend -O -m videosdb -c  \
&& \
docker compose -f $compose_file run  --rm backend -m pytest \
&& \
docker compose -f $compose_file run frontend yarn generate-and-start\

# if [[ -z "${PROJECT_ID}" ]]; then
#     docker compose -f $compose_file down
# fi
