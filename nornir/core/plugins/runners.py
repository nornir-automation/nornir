from typing import Any, List, Type

from nornir.core.task import AggregatedResult, Task
from nornir.core.inventory import Host
from nornir.core.plugins.register import PluginRegister

from typing_extensions import Protocol


RUNNERS_PLUGIN_PATH = "nornir.plugins.runners"


class RunnerPlugin(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        This method configures the plugin
        """
        raise NotImplementedError("needs to be implemented by the plugin")

    def run(self, task: Task, hosts: List[Host]) -> AggregatedResult:
        """
        This method runs the given task over all the hosts
        """
        raise NotImplementedError("needs to be implemented by the plugin")


RunnersPluginRegister: PluginRegister[Type[RunnerPlugin]] = PluginRegister(
    RUNNERS_PLUGIN_PATH
)
