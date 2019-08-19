from nornir.core.task import Result, Task


def netconf_capabilities(task: Task) -> Result:
    manager = task.host.get_connection("netconf", task.nornir.config)
    capabilities = [capability for capability in manager.server_capabilities]
    return Result(host=task.host, result=capabilities)


def test_netconf(netconf):
    result = netconf.run(netconf_capabilities)

    for _, v in result.items():
        assert "urn:ietf:params:netconf:capability:writable-running:1.0" in v.result
