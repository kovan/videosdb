
export TAG="${TAG:-$(git rev-parse --short HEAD)}"
docker-compose pull --no-parallel $@
docker-compose up -d --no-build $@

# warm up:
until curl http://localhost:3000 > /dev/null
do
    sleep 1
done

