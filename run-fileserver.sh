#!/bin/bash


export TAG=$(git rev-parse --short HEAD) 
export REPO="desktop-k:5000/"
docker-compose -f docker-compose.fileserver.yml pull --no-parallel
docker-compose -f docker-compose.fileserver.yml up  --no-build -d
