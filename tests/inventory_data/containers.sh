#!/bin/bash

start () {
    docker run -d -p 65001:22 --name host1.group_1 --hostname=host1.group_1 dbarroso/stupid_ssh_container
    docker run -d -p 65002:22 --name host2.group_1 --hostname=host2.group_1 dbarroso/stupid_ssh_container
    docker run -d -p 65003:22 --name host3.group_2 --hostname=host3.group_2 dbarroso/stupid_ssh_container
    docker run -d -p 65004:22 --name host4.group_2 --hostname=host4.group_2 dbarroso/stupid_ssh_container
}

stop () {
    docker rm -f host1.group_1
    docker rm -f host2.group_1
    docker rm -f host3.group_2
    docker rm -f host4.group_2
}

if [ "$1" == "start" ]; then
    start
elif [ "$1" == "stop" ]; then
    stop
fi
