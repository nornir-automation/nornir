#!/bin/bash

# Start NetBox, Postgres, and Nginx
docker-compose up -d > /dev/null &&

# Wait until all containers have been initialized
sleep 30s

# Import test data
./import/import_all.py
