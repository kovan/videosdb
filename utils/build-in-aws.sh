#/bin/bash

aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 570555265801.dkr.ecr.ap-south-1.amazonaws.com
export REPO=570555265801.dkr.ecr.ap-south-1.amazonaws.com/
export TAG=$(git rev-parse --short HEAD) 
docker buildx bake --push 
for service in db backend
do
    docker tag $REPO$service:$TAG $REPO$service:latest
done
