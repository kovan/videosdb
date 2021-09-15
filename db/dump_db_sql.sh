#!/bin/bash
echo $POSTGRES_PASSWORD |docker exec -i videosdb_db_1 nice -n 10 pg_dump -d postgres -h db -U postgres  > sadhguru-dump.sql
#echo nithyananda |docker-compose run --rm db pg_dump -d nithyananda -h db -U nithyananda  > nithyananda-dump.sql
#gzip sadhguru-dump.sql
#gzip nithyananda-dump.sql

