#!/bin/sh
sudo service docker start

 
# STEP 1:  build everything and start supporting apps:
docker compose build
docker compose up --detach

sleep 3

# STEP 2: Fill database and generate webpages:

docker compose run --rm \
    backend \
    poetry run \
      python -m videosdb \
        --check-for-new-videos \
        --exclude-transcripts \
&& \
docker compose run --rm \
    frontend \
    yarn generate
    
docker compose down