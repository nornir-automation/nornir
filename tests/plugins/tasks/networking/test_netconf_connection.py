from nornir.core.task import Result, Task
from nornir.plugins.tasks import networking


def get_task(task: Task, path: str = "", filter_type: str = "xpath") -> Result:
    manager = task.host.get_connection("netconf", task.nornir.config)
    params = {}
    if path:
        params["filter"] = (filter_type, path)
    result = manager.get(**params)

    return Result(host=task.host, result=result.data_xml)


class Test:
    def test_netconf_connection_non_existent_ssh_config(self, netconf):
        netconf = netconf.filter(name="netconf2.no_group")
        assert netconf.inventory.hosts

        netconf.config.ssh.config_file = "i dont exist"
        result = netconf.run(networking.netconf_capabilities)
        assert result

        for _, v in result.items():
            assert not isinstance(v.exception, FileNotFoundError)
