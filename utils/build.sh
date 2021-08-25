#/bin/bash

export REPO="pi:5000/"
export BRANCH=$(git branch --show-current)
docker buildx bake --push
