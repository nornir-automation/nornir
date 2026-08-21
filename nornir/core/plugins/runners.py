from __future__ import annotations

from typing import Any, Protocol

from nornir.core.inventory import Host
from nornir.core.plugins.register import PluginRegister
from nornir.core.task import AggregatedResult, Task

RUNNERS_PLUGIN_PATH = "nornir.plugins.runners"


class RunnerPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin."""
        raise NotImplementedError("needs to be implemented by the plugin")

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all the hosts."""
        raise NotImplementedError("needs to be implemented by the plugin")


RunnersPluginRegister: PluginRegister[type[RunnerPlugin]] = PluginRegister(RUNNERS_PLUGIN_PATH)
