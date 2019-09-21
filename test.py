from nornir import InitNornir
from nornir.core.task import Result, Task

nr = InitNornir(
    inventory={
        "options": {
            "hosts": {
                "rtr00": {
                    "hostname": "localhost",
                    "username": "admin",
                    "password": "admin",
                    "port": 65030,
                    "platform": "whatever",
                    "connection_options": {
                        "netconf": {"extras": {"hostkey_verify": False}}
                    },
                }
            }
        }
    }
)


def netconf_code(task: Task) -> Result:
    manager = task.host.get_connection("netconf", task.nornir.config)

    # get running config and system state
    print(manager.get())

    # get only hostname
    print(manager.get(filter=("xpath", "/sys:system/sys:hostname")))

    # get candidate config
    print(manager.get_config("candidate"))

    # lock
    print(manager.lock("candidate"))

    # edit configuration
    res = manager.edit_config(
        "candidate",
        "<sys:system><sys:hostname>asd</sys:hostname></sys:system>",
        default_operation="merge",
    )
    print(res)

    print(manager.commit())

    # unlock
    print(manager.unlock("candidate"))

    return Result(result="ok", host=task.host)


nr.run(task=netconf_code)
