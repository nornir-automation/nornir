import os

import paramiko


def paramiko_connection(task=None):
    """
    This tasks connects to the device with paramiko to the device and sets the
    relevant connection.
    """
    host = task.host

    client = paramiko.SSHClient()
    client._policy = paramiko.WarningPolicy()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    ssh_config_file = task.nornir.config.ssh_config_file
    if os.path.exists(ssh_config_file):
        with open(ssh_config_file) as f:
            ssh_config.parse(f)

    parameters = {
        "hostname": host.host,
        "username": host.username,
        "password": host.password,
        "port": host.ssh_port,
    }

    user_config = ssh_config.lookup(host.host)
    for k in ("hostname", "username", "port"):
        if k in user_config:
            parameters[k] = user_config[k]

    if "proxycommand" in user_config:
        parameters["sock"] = paramiko.ProxyCommand(user_config["proxycommand"])

    # TODO configurable
    #  if ssh_key_file:
    #      parameters['key_filename'] = ssh_key_file
    if "identityfile" in user_config:
        parameters["key_filename"] = user_config["identityfile"]

    client.connect(**parameters)
    host.connections["paramiko"] = client
