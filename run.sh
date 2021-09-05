export REPO="pi:5000/"
git pull
export TAG="$(git rev-parse --short HEAD)"
docker-compose pull --no-parallel
docker-compose up -d --no-build

