FROM postgres:13.2-alpine



COPY create_postgres_db.sh /docker-entrypoint-initdb.d/
WORKDIR /app
COPY sadhguru-dump.sql.gz /app/

ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT
