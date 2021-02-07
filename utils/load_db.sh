export REPO=570555265801.dkr.ecr.ap-south-1.amazonaws.com/videosdb:
backends="backend-sadhguru backend-nithyananda"
for backend in $backends
do
	gunzip backend/data.$backend.json.gz

	docker-compose run --rm $backend poetry run python manage.py loaddata --format json - < backend/data.$backend.json
done
