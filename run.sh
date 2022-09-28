#!/bin/bash


help()
{
         echo -g: generate deploy webpage
         echo -t: run tests

}

common() {

    if  ! [[ -z "$BRANCH_NAME" ]]
    then
        export REPO=grc.io/$PROJECT_NAME/$BRANCH_NAME/
        docker-compose pull frontend backend
    else
        pgrep docker > /dev/null || sudo service docker start
    fi
    rm -fr ./dist

}

generate() {
    common
    docker compose --profile generate run backend run main -c \
    && \
    docker compose --profile generate run frontend \
    && \
    docker compose cp frontend:/app/dist ./frontend \
    || exit -1
    # && \
    # docker compose --profile generate run firebase\

}

runtests() {
    common

    docker compose build \
    && \
    docker compose --profile tests run backend-tests \
    && \
    docker compose --profile tests run frontend-tests \
    && \
    docker compose --profile end2end-tests run backend \
    && \
    docker compose --profile end2end-tests run frontend\
    || exit -1

    docker compose down
}

while getopts ":hgt" option; do
   case $option in
      g) generate
         exit;;
      t) runtests
         exit;;
      h) help
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done






