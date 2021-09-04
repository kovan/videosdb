#/bin/bash

sudo service docker start
export REPO="pi:5000/"
export TAG="$(git rev-parse --short HEAD)"
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx bake --set '*.platform=linux/arm/v7' --push 
