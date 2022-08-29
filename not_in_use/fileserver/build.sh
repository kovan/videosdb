REPO=desktop-k:5000/ TAG=latest docker buildx bake -f docker-compose.fileserver.yml --set "*.platform=linux/arm/v7" --push
