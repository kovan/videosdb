#!/bin/bash
echo $POSTGRES_PASSWORD |docker exec -ti videosdb_db_1 psql -d postgres -U postgres 
