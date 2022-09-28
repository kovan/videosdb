#!/bin/bash

Help()
{
    echo -g: generate deploy webpage
    echo -t: run tests

}

SetUp() {

    REPO_PROJECT=worpdress-279321

    if  ! [[ -z "$BRANCH_NAME" ]] # we are in GCP
    then
        REPO=grc.io/$REPO_PROJECT/$BRANCH_NAME/

    else
        pgrep docker > /dev/null || sudo service docker start
    fi

    docker compose build  --pull || exit -1

    rm -fr ./dist
}

TearDown() {
    docker compose push
    docker compose down
}

Generate() {
    docker compose run backend run main -c || exit -1
    docker compose run frontend yarn generate|| exit -1
    docker compose cp frontend:/app/dist ./frontend || exit -1
    # docker compose run firebase || exit -1
}



while getopts "gfbeh" option; do
    SetUp
    case $option in
        g) Generate
        exit;;
        f) docker compose build frontend
            docker compose --profile tests run frontend yarn test || exit -1
        exit;;
        b)
            docker compose build backend
            docker-compose --profile tests up --build -d || exit -1
            docker compose --profile tests run -e FIRESTORE_EMULATOR_HOST=localhost:8080 \
            backend run python -m unittest || exit -1
        exit;;
        e) docker compose build backend frontend || exit -1
            docker compose --profile end2end-tests up --build -d || exit -1
            docker compose run backend || exit -1
            docker compose run frontend || exit -1
        exit;;
        h) Help
        exit;;
    esac
    TearDown
done






