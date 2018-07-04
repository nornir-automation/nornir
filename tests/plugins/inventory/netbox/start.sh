#!/bin/bash

# Start NetBox, Postgres, and Nginx
echo "Starting NetBox"
docker-compose up -d > /dev/null &

# Wait until all containers have been initialized
sleep 60s

# Import test data in the correct order
echo "Importing data"
./import/1_add_sites.py
./import/2_add_roles.py
./import/3_add_manufacturers.py
./import/4_add_devtypes.py
./import/5_add_platforms.py
./import/6_add_devices.py
./import/7_add_interfaces.py
./import/8_add_addresses.py
./import/9_set_primary_ip.py