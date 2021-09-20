#/bin/bash

sudo service docker start
export REPO=${REPO:-desktop-k:5000/}
export TAG=${TAG:-$(git rev-parse --short HEAD)}
#export PLATFORM= #linux/arm/v7'
if [[ $PLATFORM == linux/arm/v7 ]]
then
	docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
fi
		
docker buildx bake --push --set "*.platform=$PlATFORM" -f docker-compose.yml -f docker-compose.fileserver.yml $@
for service in db backend
do
    docker tag $REPO$service:$TAG $REPO$service:latest
done
