#!/bin/sh
pgrep docker || sudo service docker start



rm -fr ./dist

docker compose build \
&& \
docker compose --profile tests run backend-tests \
&& \
docker compose --profile tests run frontend-tests \
&& \
docker compose --profile end2end-tests run backend \
&& \
docker compose --profile end2end-tests run frontend\


#docker compose down

