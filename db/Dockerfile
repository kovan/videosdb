FROM postgres

COPY create_postgres_db.sh /docker-entrypoint-initdb.d/
WORKDIR /app
COPY --chmod=666 *.gz /app/