import logging
import logging.config
import types
from typing import Any, Callable, Dict, Generator, List, Optional, Type

from nornir.core.configuration import Config
from nornir.core.exceptions import PluginNotRegistered
from nornir.core.inventory import Inventory
from nornir.core.plugins.runners import RunnerPlugin
from nornir.core.processor import Processor, Processors
from nornir.core.state import GlobalState
from nornir.core.task import AggregatedResult, Task

logger = logging.getLogger(__name__)


class Nornir:
    """
    This is the main object to work with. It contains the inventory and it serves
    as task dispatcher.

    Arguments:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(GlobalState): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration object

    Attributes:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(:obj:`nornir.core.GlobalState`): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration parameters
    """

    def __init__(
        self,
        inventory: Inventory,
        config: Optional[Config] = None,
        data: Optional[GlobalState] = None,
        processors: Optional[Processors] = None,
        runner: Optional[RunnerPlugin] = None,
    ) -> None:
        self.data = data if data is not None else GlobalState()
        self.inventory = inventory
        self.config = config or Config()
        self.processors = processors or Processors()
        self._runner = runner

    def __enter__(self) -> "Nornir":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[types.TracebackType] = None,
    ) -> None:
        self.close_connections(on_good=True, on_failed=True)

    def with_processors(self, processors: List[Processor]) -> "Nornir":
        """
        Given a list of Processor objects return a copy of the nornir object with the processors
        assigned to the copy. The original object is left unmodified.
        """
        return Nornir(**{**self._clone_parameters(), **{"processors": Processors(processors)}})

    def with_runner(self, runner: RunnerPlugin) -> "Nornir":
        """
        Given a runner return a copy of the nornir object with the runner
        assigned to the copy. The original object is left unmodified.
        """
        return Nornir(**{**self._clone_parameters(), **{"runner": runner}})

    def filter(self, *args: Any, **kwargs: Any) -> "Nornir":
        """
        See :py:meth:`nornir.core.inventory.Inventory.filter`

        Returns:
            :obj:`Nornir`: A new object with same configuration as ``self`` but filtered inventory.
        """
        b = Nornir(**self._clone_parameters())
        b.inventory = self.inventory.filter(*args, **kwargs)
        return b

    def run(
        self,
        task: Callable[..., Any],
        raise_on_error: Optional[bool] = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> AggregatedResult:
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            raise_on_error (``bool``): Override raise_on_error behavior
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            **kwargs: additional argument to pass to ``task`` when calling it

        Raises:
            :obj:`nornir.core.exceptions.NornirExecutionError`: if at least a task fails
              and self.config.core.raise_on_error is set to ``True``

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: results of each execution
        """
        run_task = Task(
            task,
            self,
            global_dry_run=self.data.dry_run,
            name=name,
            processors=self.processors,
            **kwargs,
        )
        self.processors.task_started(run_task)

        run_on = []
        if on_good:
            for hostname, host in self.inventory.hosts.items():
                if hostname not in self.data.failed_hosts:
                    run_on.append(host)
        if on_failed:
            for hostname, host in self.inventory.hosts.items():
                if hostname in self.data.failed_hosts:
                    run_on.append(host)

        num_hosts = len(run_on)
        if num_hosts:
            logger.info(
                "Running task %r with args %s on %d hosts",
                run_task.name,
                kwargs,
                num_hosts,
            )
        else:
            logger.warning("Task %r has not been run – 0 hosts selected", run_task.name)

        result = self.runner.run(run_task, run_on)

        raise_on_error = (
            raise_on_error if raise_on_error is not None else self.config.core.raise_on_error
        )
        if raise_on_error:
            result.raise_on_error()
        else:
            self.data.failed_hosts.update(result.failed_hosts.keys())

        self.processors.task_completed(run_task, result)

        return result

    def dict(self) -> Dict[str, Any]:
        """Return a dictionary representing the object."""
        return {"data": self.data.dict(), "inventory": self.inventory.dict()}

    def close_connections(self, on_good: bool = True, on_failed: bool = False) -> None:
        def close_connections_task(task: Task) -> None:
            task.host.close_connections()

        self.run(task=close_connections_task, on_good=on_good, on_failed=on_failed)

    @property
    def runner(self) -> RunnerPlugin:
        if self._runner:
            return self._runner

        raise PluginNotRegistered("Runner plugin not registered")

    def _clone_parameters(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "inventory": self.inventory,
            "config": self.config,
            "processors": self.processors,
            "runner": self._runner,
        }

    @classmethod
    def get_validators(cls) -> Generator[Callable[["Nornir"], "Nornir"], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: "Nornir") -> "Nornir":
        if not isinstance(v, cls):
            raise ValueError(f"Nornir: Nornir expected not {type(v)}")
        return v
