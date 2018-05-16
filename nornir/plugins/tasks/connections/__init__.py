from .napalm_connection import napalm_connection
from .netmiko_connection import netmiko_connection
from .paramiko_connection import paramiko_connection


available_connections = {
    "napalm": napalm_connection,
    "netmiko": netmiko_connection,
    "paramiko": paramiko_connection,
}

__all__ = ("napalm_connection", "netmiko_connection", "paramiko_connection")
