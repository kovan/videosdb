aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 570555265801.dkr.ecr.ap-south-1.amazonaws.com
docker-compose -f docker-compose.aws.yml pull

git pull
docker-compose -f docker-compose.aws.yml up -d
docker system prune -f
