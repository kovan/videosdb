#!/bin/bash
pgrep docker || sudo service docker start

if [[ -z "$BRANCH_NAME" ]]
then
    export REPO=grc.io/$PROJECT_NAME/$BRANCH_NAME/
    docker-compose pull
fi

rm -fr ./dist




