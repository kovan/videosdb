export REPO="pi:5000/"
export BRANCH=":$(git rev-parse --abbrev-ref HEAD)"
docker-compose up -d

