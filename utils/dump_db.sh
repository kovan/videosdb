backends="backend-nithyananda"
for backend in $backends
do
    docker-compose run --rm $backend poetry run python manage.py dumpdata --natural-foreign --natural-primary > data.$backend.json
    gzip data.$backend.json
done
