#!/usr/bin/env python
import resource
import sys
import time
from typing import Any, Dict

from nornir.core.deserializer.inventory import (
    DefaultsDict,
    GroupsDict,
    HostsDict,
    Inventory,
)
from nornir.core.task import Result, Task
from nornir.init_nornir import InitNornir


class DynInv(Inventory):
    def __init__(self, num_hosts: int = 100, *args: Any, **kwargs: Any):
        hosts: HostsDict = {}
        groups: GroupsDict = {}
        defaults: DefaultsDict = {}

        for i in range(0, num_hosts):
            hosts[f"host_{i}"] = {}

        super().__init__(hosts=hosts, groups=groups, defaults=defaults, *args, **kwargs)


def wait(task: Task, sec: int, shared: Dict[str, bool]) -> Result:
    time.sleep(sec)
    shared[task.host.name] = True
    return Result(host=task.host, result=task.host.name)


def main(num_hosts: int, num_workers: int, sec: float) -> None:
    shared: Dict[str, bool] = {}
    nr = InitNornir(
        core={"num_workers": num_workers},
        inventory={"plugin": DynInv, "options": {"num_hosts": num_hosts}},
    )
    nr.run(task=wait, sec=sec, shared=shared)  # type: ignore
    assert num_hosts == len(shared)


if __name__ == "__main__":
    # TODO: measure total time
    # TODO: save results to a json file
    # TODO: compare with previous results and error if it deviates a certain %
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} NUM_HOSTS NUM_WORKERS SLEEP")
        sys.exit(1)
    num_hosts = int(sys.argv[1])
    num_workers = int(sys.argv[2])
    sec = float(sys.argv[3])
    main(num_hosts, num_workers, sec)
    res = resource.getrusage(resource.RUSAGE_SELF)
    print(f"ru_utime: {res.ru_utime}")
    print(f"ru_stime: {res.ru_stime}")
    print(f"maxrss: {res.ru_maxrss}")
