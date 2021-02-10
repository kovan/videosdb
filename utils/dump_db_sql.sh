echo posgres |docker-compose run --rm db pg_dump -d postgres -h db -U postgres  > sadhguru-dump.sql
echo nithyananda |docker-compose run --rm db pg_dump -d nithyananda -h db -U postgres  > nithyananda-dump.sql
gzip sadhguru-dump.sql
gzip nithyananda-dump.sql