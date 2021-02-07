backends="backend-nithyananda"
for backend in $backends
do
    docker-compose run --rm $backend poetry run python manage.py dumpdata --natural-foreign --natuaral-primary > data.$backend.json
    gzip data.$backend.json
done
