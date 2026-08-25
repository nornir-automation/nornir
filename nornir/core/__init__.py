from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nornir.core.configuration import Config
from nornir.core.exceptions import PluginNotRegistered
from nornir.core.inventory import Inventory
from nornir.core.plugins.runners import RunnerPlugin
from nornir.core.processor import Processor, Processors
from nornir.core.state import GlobalState
from nornir.core.task import AggregatedResult, Task

if TYPE_CHECKING:
    import builtins
    import types
    from collections.abc import Callable, Generator

logger = logging.getLogger(__name__)


class Nornir:
    """Main object to work with.

    It contains the inventory and it serves as task dispatcher.

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
        config: Config | None = None,
        data: GlobalState | None = None,
        processors: Processors | None = None,
        runner: RunnerPlugin | None = None,
    ) -> None:
        self.data = data if data is not None else GlobalState()
        self.inventory = inventory
        self.config = config or Config()
        self.processors = processors or Processors()
        self._runner = runner

    def __enter__(self) -> Nornir:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: types.TracebackType | None = None,
    ) -> None:
        self.close_connections(on_good=True, on_failed=True)

    def with_processors(self, processors: list[Processor]) -> Nornir:
        """Return a copy of the object with the given processors assigned to it.

        The original object is left unmodified.

        Returns:
            :obj:`Nornir`: A copy of ``self`` with the given processors assigned.

        """
        return Nornir(**{**self._clone_parameters(), **{"processors": Processors(processors)}})

    def with_runner(self, runner: RunnerPlugin) -> Nornir:
        """Return a copy of the object with the given runner assigned to it.

        The original object is left unmodified.

        Returns:
            :obj:`Nornir`: A copy of ``self`` with the given runner assigned.

        """
        return Nornir(**{**self._clone_parameters(), **{"runner": runner}})

    def filter(self, *args: Any, **kwargs: Any) -> Nornir:
        """Return a copy of the object with a filtered inventory.

        See :py:meth:`nornir.core.inventory.Inventory.filter` for the accepted arguments.

        Returns:
            :obj:`Nornir`: A new object with same configuration as ``self`` but filtered inventory.

        """
        b = Nornir(**self._clone_parameters())
        b.inventory = self.inventory.filter(*args, **kwargs)
        return b

    def run(
        self,
        task: Callable[..., Any],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        **kwargs: Any,
    ) -> AggregatedResult:
        """Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            raise_on_error (``bool``): Override raise_on_error behavior
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            name (``str``): Name of the task, defaults to the name of the ``task`` callable
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: results of each execution

        Raises:
            nornir.core.exceptions.NornirExecutionError: if at least a task fails
              and self.config.core.raise_on_error is set to ``True``

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

    def dict(self) -> dict[str, Any]:
        """Return a dictionary representing the object.

        Returns:
            The ``data`` and ``inventory`` attributes serialized as dictionaries.

        """
        return {"data": self.data.dict(), "inventory": self.inventory.dict()}

    def close_connections(self, on_good: bool = True, on_failed: bool = False) -> None:
        """Close all the connections open on the hosts of the inventory.

        The connections are closed by running a task, so the call goes through the
        runner and the processors see it like any other task. Using the object as a
        context manager closes the connections of every host on exit, failed ones
        included.

        Arguments:
            on_good(``bool``): Whether to close the connections of the hosts marked as good
            on_failed(``bool``): Whether to close the connections of the hosts marked as failed

        """

        def close_connections_task(task: Task) -> None:
            task.host.close_connections()

        self.run(task=close_connections_task, on_good=on_good, on_failed=on_failed)

    @property
    def runner(self) -> RunnerPlugin:
        """The runner this object dispatches its tasks with.

        Returns:
            :obj:`nornir.core.plugins.runners.RunnerPlugin`: The runner assigned to ``self``.

        Raises:
            nornir.core.exceptions.PluginNotRegistered: no runner was assigned. Objects
                built by :obj:`nornir.InitNornir` always have one, so this is only
                reachable when constructing :obj:`Nornir` directly.

        """
        if self._runner:
            return self._runner

        raise PluginNotRegistered("Runner plugin not registered")

    def _clone_parameters(self) -> builtins.dict[str, Any]:
        return {
            "data": self.data,
            "inventory": self.inventory,
            "config": self.config,
            "processors": self.processors,
            "runner": self._runner,
        }

    @classmethod
    def get_validators(cls) -> Generator[Callable[[Nornir], Nornir], None, None]:
        """Yield the validators used to accept a :obj:`Nornir` as a field of a model.

        Yields:
            :py:meth:`validate`.

        """
        # Left over from the time nornir modelled its objects with pydantic. Nothing in
        # nornir calls it, and the name does not match the hook any released pydantic
        # looks for (__get_validators__ in v1, __get_pydantic_core_schema__ in v2), so
        # it has no effect on its own.
        yield cls.validate

    @classmethod
    def validate(cls, v: Nornir) -> Nornir:
        """Return ``v`` unchanged if it is a :obj:`Nornir` object.

        Returns:
            :obj:`Nornir`: The object that was passed in.

        Raises:
            ValueError: ``v`` is not an instance of this class.

        """
        # Counterpart of get_validators, and equally unused.
        if not isinstance(v, cls):
            raise ValueError(f"Nornir: Nornir expected not {type(v)}")
        return v
