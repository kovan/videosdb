#!/bin/sh


 
# STEP 1:  build everything and start supporting apps:
docker compose build
docker compose up --detach

# STEP 2: Fill database:

docker compose run --rm \
    backend \
    poetry run \
      python -m videosdb \
        --check-for-new-videos \
&& \
# STEP 3: Generate static site 

docker compose run --rm \
    frontend \
    yarn generate
    
