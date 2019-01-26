#!/bin/bash
DIR1=/mnt/ipfs-docker-data
DIR2=/mnt/ipfs-docker-staging
rm -fr $DIR1
rm -fr $DIR2
mkdir $DIR1
mkdir $DIR2

CID=$(docker run -d --name ipfs-node \
	--restart always\
        --network ee-global-frontend-network\
   -v $DIR2:/export -v $DIR1:/data/ipfs \
   -p 4001:4001 -p 5001:5001 \
  jbenet/go-ipfs:latest)
docker exec $CID ipfs config profile apply server
