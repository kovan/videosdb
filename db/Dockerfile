FROM postgres:13.2-alpine
ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT

COPY create_postgres_db.sh /docker-entrypoint-initdb.d/
WORKDIR /app
COPY sadhguru-dump.sql.gz /app/
