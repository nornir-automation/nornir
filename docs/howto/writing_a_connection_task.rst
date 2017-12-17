Writing a connection task
#########################

Connection tasks are tasks that establish a connection with a device to provide some sort of reusable mechanism to interact with it. You can find some examples of connections tasks in the :doc:`../ref/tasks/connections` section.

Writing a connection task is no different from writing a regular task. The only difference is that the task will have to establish the connection and assign it to the device.

A continuation you can see a simplified version of the ``paramiko_connection`` connection task as an example::

    def paramiko_connection(task=None):
        host = task.host

        client = paramiko.SSHClient()

        parameters = {
            "hostname": host.host,
            "username": host.username,
            "password": host.password,
            "port": host.ssh_port,
        }
        client.connect(**parameters)
        host.connections["paramiko"] = client

Note the last line where the connection is assigned to the host. Subsequent tasks will be able to retrieve this connection by host calling ``host.get_connection("paramiko")``
