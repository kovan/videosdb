#/bin/bash

sudo service docker start
export REPO=${REPO:-desktop-k:5000/}
export TAG=${TAG:-$(git rev-parse --short HEAD)}
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx bake --push --set '*.platform=linux/arm/v7'  $@
