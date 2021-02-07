backends="backend-sadhguru backend-nithyananda"
for backend in $backends
do
	gunzip backend/data.$backend.json.gz
	docker-compose run --rm $backend poetry run python manage.py loaddata --format json - < backend/data.$backend.json
done
