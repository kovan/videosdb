#!/bin/sh

yarn config set cache-folder $YARN_CACHE_FOLDER


# Call command issued to the docker service
exec "$@"
