#!/bin/sh
docker build -q -t videosdb-builder utils/builder
docker run --rm --workdir /app  -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd):/app videosdb-builder:latest  $*
