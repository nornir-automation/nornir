#!/bin/bash

start () {
    docker run -d -p 65001:22 --name dev1.group_1 --hostname=dev1.group_1 dbarroso/stupid_ssh_container
    docker run -d -p 65002:22 --name dev2.group_1 --hostname=dev2.group_1 dbarroso/stupid_ssh_container
    docker run -d -p 65003:22 --name dev3.group_2 --hostname=dev3.group_2 dbarroso/stupid_ssh_container
    docker run -d -p 65004:22 --name dev4.group_2 --hostname=dev4.group_2 dbarroso/stupid_ssh_container
}

stop () {
    docker rm -f dev1.group_1
    docker rm -f dev2.group_1
    docker rm -f dev3.group_2
    docker rm -f dev4.group_2
}

if [ "$1" == "start" ]; then
    start
elif [ "$1" == "stop" ]; then
    stop
fi
