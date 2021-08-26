#/bin/bash

export REPO="localhost:5000/"
export TAG="$(git branch --show-current)"
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#docker buildx create --name mybuilder 
#docker buildx use mybuilder
#docker buildx inspect --bootstrap
docker buildx bake --set '*.platform=linux/arm/v7' --push
