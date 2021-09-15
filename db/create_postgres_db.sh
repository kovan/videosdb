#!/bin/bash
set -e

#  CREATE DATABASE videosdb;
#  CREATE USER myuser WITH ENCRYPTED PASSWORD 'mypass';
#  ALTER ROLE myuser SET client_encoding TO 'utf8';
#  ALTER ROLE myuser SET default_transaction_isolation TO 'read committed';
#  ALTER ROLE myuser SET timezone TO 'UTC';
#  ALTER USER myuser CREATEDB;
#  GRANT ALL PRIVILEGES ON DATABASE videosdb TO myuser;



# psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
# 	CREATE USER nithyananda WITH ENCRYPTED PASSWORD 'nithyananda';
# 	CREATE DATABASE nithyananda;
# 	GRANT ALL PRIVILEGES ON DATABASE nithyananda TO nithyananda;
# EOSQL

cat /app/sadhguru-dump.sql | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres
cat "ALTER USER postgres PASSWORD $POSTGRES_PASSWORD;"| psql --username "$POSTGRES_USER" --dbname postgres
#gunzip -c /app/nithyananda-dump.sql.gz | psql -v ON_ERROR_STOP=1 --username  nithyananda     --dbname nithyananda
