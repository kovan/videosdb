git pull
git checkout prod
docker-compose -f docker-compose.gcp.yml pull
docker-compose -f docker-compose.gcp.yml up -d
docker system prune -f
