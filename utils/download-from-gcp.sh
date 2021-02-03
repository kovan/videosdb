git pull
git checkout prod
docker-compose pull
docker-compose up -d
sleep 5
docker system prune -f

root_url=gcr.io/worpdress-279321/videosdb

for i in backend frontend postgres
do
    for sha in $(gcloud container images list-tags $root_url-$i --filter='-tags:*'  --format="get(digest)" --limit=9999999)
    do
        gcloud container images delete $root_url-$i@$sha --quiet
    done
done

# to delete all images remove the --filterº