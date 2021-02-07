git checkout prod
git pull
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 570555265801.dkr.ecr.ap-south-1.amazonaws.com
export REPO=570555265801.dkr.ecr.ap-south-1.amazonaws.com/videosdb:
docker-compose pull
docker-compose up --no-build -d
docker system prune -f
