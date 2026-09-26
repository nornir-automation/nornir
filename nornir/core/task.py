from __future__ import annotations

import functools
import inspect
import logging
import traceback
from typing import TYPE_CHECKING, Any, cast

from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    NornirExecutionError,
    NornirSubTaskError,
    SyncTaskOnAsyncRunError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from nornir.core import Nornir
    from nornir.core.inventory import Host
    from nornir.core.processor import Processors


logger = logging.getLogger(__name__)
DEFAULT_SEVERITY_LEVEL = logging.INFO


def _is_coroutine_task(task: Callable[..., Any]) -> bool:
    """Return whether a task callable must be awaited.

    Returns:
        Whether the callable is implemented asynchronously.

    """
    while isinstance(task, functools.partial):
        task = task.func
    return inspect.iscoroutinefunction(task) or inspect.iscoroutinefunction(type(task).__call__)


def _get_task_name(task: Callable[..., Any], name: str | None = None) -> str:
    """Return a safe name for task mismatch diagnostics.

    Returns:
        The explicit name, callable name, or callable type name.

    """
    if name is not None:
        return name
    try:
        task_name = getattr(task, "__name__", None)
    except Exception:
        task_name = None
    return task_name if isinstance(task_name, str) else type(task).__name__


class Task:
    """Wrapper around a function that has to be run against multiple devices.

    You won't probably have to deal with this class yourself as
    :meth:`nornir.core.Nornir.run` will create it automatically.

    Arguments:
        task (callable): function or callable we will be calling
        name (``string``): name of task, defaults to ``task.__name__``
        severity_level (logging.LEVEL): Severity level associated to the task
        **kwargs: Parameters that will be passed to the ``task``

    Attributes:
        task (callable): function or callable we will be calling
        name (``string``): name of task, defaults to ``task.__name__``
        params: Parameters that will be passed to the ``task``.
        self.results (:obj:`nornir.core.task.MultiResult`): Intermediate results
        host (:obj:`nornir.core.inventory.Host`): Host we are operating with. Populated right
          before calling the ``task``
        nornir(:obj:`nornir.core.Nornir`): Populated right before calling
          the ``task``
        severity_level (logging.LEVEL): Severity level associated to the task

    """

    def __init__(
        self,
        task: Callable[..., Any],
        nornir: Nornir,
        global_dry_run: bool,
        processors: Processors,
        name: str | None = None,
        severity_level: int = DEFAULT_SEVERITY_LEVEL,
        parent_task: Task | None = None,
        **kwargs: str,
    ) -> None:
        self.task = task
        self.nornir = nornir
        self.name = name or task.__name__
        self.global_dry_run = global_dry_run
        self.parent_task = parent_task
        self.params = kwargs
        self.results = MultiResult(self.name)
        self.severity_level = severity_level
        self.processors = processors

    def copy(self) -> Task:
        """Return a copy of this task with no host and no results yet.

        :py:meth:`start` records the host it ran against and the results it produced on
        the task object itself, so the runners hand each host its own copy rather than
        sharing one task across hosts.

        Returns:
            :obj:`Task`: A task with the same callable, parameters, processors and
            severity level as ``self``.

        """
        return Task(
            self.task,
            self.nornir,
            self.global_dry_run,
            self.processors,
            self.name,
            self.severity_level,
            self.parent_task,
            **self.params,
        )

    def __repr__(self) -> str:
        return self.name

    def _begin(self, host: Host) -> None:
        self.host = host
        if self.parent_task is not None:
            self.processors.subtask_instance_started(self, host)
        else:
            self.processors.task_instance_started(self, host)

    def _result_from_exception(self, exception: Exception, traceback_text: str) -> Result:
        logger.error("Host %r: task %r failed", self.host.name, self.name, exc_info=exception)
        result = str(exception) if isinstance(exception, NornirSubTaskError) else traceback_text
        return Result(self.host, exception=exception, result=result, failed=True)

    def _finish(self, host: Host, result: Any) -> MultiResult:
        if not isinstance(result, Result):
            result = Result(host=host, result=result)
        result.name = self.name

        if result.severity_level == DEFAULT_SEVERITY_LEVEL:
            if result.failed:
                result.severity_level = logging.ERROR
            else:
                result.severity_level = self.severity_level

        self.results.insert(0, result)
        if self.parent_task is not None:
            self.processors.subtask_instance_completed(self, host, self.results)
        else:
            self.processors.task_instance_completed(self, host, self.results)
        return self.results

    def start(self, host: Host) -> MultiResult:
        """Run the task for the given host.

        Arguments:
            host (:obj:`nornir.core.inventory.Host`): Host we are operating with. Populated right
              before calling the ``task``

        Returns:
            :obj:`nornir.core.task.MultiResult`: Results of the task and its subtasks

        """
        self._begin(host)
        try:
            logger.debug("Host %r: running task %r", self.host.name, self.name)
            r = self.task(self, **self.params)
        except Exception as e:
            r = self._result_from_exception(e, traceback.format_exc())
        return self._finish(host, r)

    async def astart(self, host: Host) -> MultiResult:
        """Run the asynchronous task for the given host.

        Arguments:
            host (:obj:`nornir.core.inventory.Host`): Host we are operating with. Populated right
              before calling the ``task``

        Returns:
            :obj:`nornir.core.task.MultiResult`: Results of the task and its subtasks

        """
        self._begin(host)
        try:
            logger.debug("Host %r: running task %r", self.host.name, self.name)
            r = await self.task(self, **self.params)
        except Exception as e:
            r = self._result_from_exception(e, traceback.format_exc())
        return self._finish(host, r)

    def _create_subtask(self, task: Callable[..., Any], kwargs: dict[str, Any]) -> Task:
        if "severity_level" not in kwargs:
            kwargs["severity_level"] = self.severity_level
        return Task(
            task,
            self.nornir,
            global_dry_run=self.global_dry_run,
            processors=self.processors,
            parent_task=self,
            **kwargs,
        )

    def _record_subtask_result(self, task: Task, result: MultiResult) -> MultiResult:
        self.results.append(result[0] if len(result) == 1 else cast("Result", result))
        if result.failed:
            # Without this we will keep running the grouped task
            raise NornirSubTaskError(task=task, result=result)
        return result

    def run(self, task: Callable[..., Any], **kwargs: Any) -> MultiResult:
        """Call a task from within a task.

        For instance::

            def grouped_tasks(task):
                task.run(my_first_task)
                task.run(my_second_task)

            nornir.run(grouped_tasks)

        This method will ensure the subtask is run only for the host in the current thread.

        Returns:
            :obj:`nornir.core.task.MultiResult`: Results of the subtask and its own subtasks

        Raises:
            Exception: the ``host`` attribute has not been set, which happens when calling
                this from outside a nested task
            nornir.core.exceptions.AsyncTaskOnSyncRunError: the subtask is asynchronous
            nornir.core.exceptions.NornirSubTaskError: the subtask failed

        """
        if not self.host:
            msg = (
                "You have to call this after setting host and nornir attributes. ",
                "You probably called this from outside a nested task",
            )
            raise Exception(msg)

        if _is_coroutine_task(task):
            raise AsyncTaskOnSyncRunError(_get_task_name(task, kwargs.get("name")))

        run_task = self._create_subtask(task, kwargs)
        r = run_task.start(self.host)
        return self._record_subtask_result(run_task, r)

    async def arun(
        self,
        task: Callable[..., Coroutine[Any, Any, Any]],
        **kwargs: Any,
    ) -> MultiResult:
        """Call an asynchronous task from within an asynchronous task.

        Returns:
            :obj:`nornir.core.task.MultiResult`: Results of the subtask and its own subtasks

        Raises:
            Exception: the ``host`` attribute has not been set, which happens when calling
                this from outside a nested task
            nornir.core.exceptions.SyncTaskOnAsyncRunError: the subtask is synchronous
            nornir.core.exceptions.NornirSubTaskError: the subtask failed

        """
        if not self.host:
            msg = (
                "You have to call this after setting host and nornir attributes. ",
                "You probably called this from outside a nested task",
            )
            raise Exception(msg)

        if not _is_coroutine_task(task):
            raise SyncTaskOnAsyncRunError(_get_task_name(task, kwargs.get("name")))

        run_task = self._create_subtask(task, kwargs)
        r = await run_task.astart(self.host)
        return self._record_subtask_result(run_task, r)

    def is_dry_run(self, override: bool | None = None) -> bool:
        """Return whether the current task is a dry run or not.

        Returns:
            ``True`` if the task is a dry run, ``False`` otherwise.

        """
        return override if override is not None else self.global_dry_run


class Result:
    """Result of running individual tasks.

    Arguments:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`nornir.core.inventory.Host`): Reference to the host that lead to this result
        failed (bool): Whether the execution failed or not
        severity_level (logging.LEVEL): Severity level associated to the result of the excecution
        exception (Exception): uncaught exception thrown during the exection of the task (if any)

    Attributes:
        changed (bool): ``True`` if the task is changing the system
        diff (obj): Diff between state of the system before/after running this task
        result (obj): Result of the task execution, see task's documentation for details
        host (:obj:`nornir.core.inventory.Host`): Reference to the host that lead ot this result
        failed (bool): Whether the execution failed or not
        severity_level (logging.LEVEL): Severity level associated to the result of the excecution
        exception (Exception): uncaught exception thrown during the exection of the task (if any)

    """

    def __init__(
        self,
        host: Host | None,
        result: Any = None,
        changed: bool = False,
        diff: str = "",
        failed: bool = False,
        exception: BaseException | None = None,
        severity_level: int = DEFAULT_SEVERITY_LEVEL,
        **kwargs: Any,
    ) -> None:
        self.result = result
        self.host = host
        self.changed = changed
        self.diff = diff
        self.failed = failed
        self.exception = exception
        self.name: str | None = None
        self.severity_level = severity_level

        self.stdout: str | None = None
        self.stderr: str | None = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}: "{self.name}"'

    def __str__(self) -> str:
        if self.exception:
            return str(self.exception)

        return str(self.result)


class MultiResult(list[Result]):
    """List-like object with the results of all the subtasks for a particular device/task."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __getattr__(self, name: str) -> Any:

        # without this pickling breaks
        if name in ["__getstate__", "__setstate__"]:
            return super().__getattribute__(name)

        return getattr(self[0], name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {super().__repr__()}"

    @property
    def failed(self) -> bool:
        """If ``True`` at least a task failed."""
        return any(h.failed for h in self)

    @property
    def changed(self) -> bool:
        """If ``True`` at least a task changed the system."""
        return any(h.changed for h in self)

    def raise_on_error(self) -> None:
        """Raise an exception if at least a task failed.

        Raises:
            nornir.core.exceptions.NornirExecutionError: When at least a task failed

        """
        if self.failed:
            raise NornirExecutionError(self)


class AggregatedResult(dict[str, MultiResult]):
    """Dict-like object that aggregates the results for all devices.

    You can access each individual result by doing ``my_aggr_result["hostname_of_device"]``.
    """

    def __init__(self, name: str, **kwargs: MultiResult) -> None:
        self.name = name
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} ({self.name}): {super().__repr__()}"

    @property
    def failed(self) -> bool:
        """If ``True`` at least a host failed."""
        return any(h.failed for h in self.values())

    @property
    def failed_hosts(self) -> dict[str, MultiResult]:
        """Hosts that failed during the execution of the task."""
        return {h: r for h, r in self.items() if r.failed}

    def raise_on_error(self) -> None:
        """Raise an exception if at least a task failed.

        Raises:
            nornir.core.exceptions.NornirExecutionError: When at least a task failed

        """
        if self.failed:
            raise NornirExecutionError(self)
