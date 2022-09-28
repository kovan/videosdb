#!/bin/bash


help()
{
         echo -g: generate deploy webpage
         echo -t: run tests

}

Common() {

    PROJECT=worpdress-279321

    if  ! [[ -z "$BRANCH_NAME" ]] # we are in GCP
    then
        REPO=grc.io/$PROJECT/$BRANCH_NAME/
        docker-compose pull frontend backend
    else
        pgrep docker > /dev/null || sudo service docker start
    fi
    rm -fr ./dist


}

Generate() {
    Common
    docker compose --profile generate run backend run main -c \
    && \
    docker compose --profile generate run frontend yarn\
    && \
    docker compose cp frontend:/app/dist ./frontend \
    || exit -1
    # && \
    # docker compose --profile generate run firebase\

}

RunTests() {
    Common

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
      g) Generate
         exit;;
      t) RunTests
         exit;;
      h) help
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done






