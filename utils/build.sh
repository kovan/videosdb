#/bin/bash

#sudo service docker start
export REPO=${REPO:-desktop-k:5000/}
export TAG=${TAG:-$(git rev-parse --short HEAD)}
export PLATFORM=${PLATFORM:-linux/amd64}

if [[ $PLATFORM == linux/arm/v7 ]]
then
	docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
fi


docker buildx bake --push --set "*.platform=$PLATFORM"  $@


for image in db backend
do
    docker tag $REPO$image:$TAG $REPO$image:latest
done
