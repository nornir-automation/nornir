from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar, cast

import pytest

from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.configuration import Config, CoreConfig
from nornir.core.exceptions import (
    SYNC_TASKS_IN_ASYNC_RUNS_ISSUE,
    AsyncTaskOnSyncRunError,
    NornirExecutionError,
    RunnerNotAsyncError,
    RunnerNotSyncError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.inventory import Defaults, Groups, Host, Hosts, Inventory
from nornir.core.plugins.connections import (
    CapabilityConnectionPluginRegister,
    ConnectionCapability,
    ConnectionPluginRegister,
)
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.core.plugins.runners import RunnersPluginRegister
from nornir.core.processor import Processors
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner

AsyncTask = Callable[..., Coroutine[Any, Any, Any]]
ProcessorEvent = tuple[
    str,
    Task,
    Host | None,
    AggregatedResult | MultiResult | None,
]


class RecordingProcessor:
    def __init__(self) -> None:
        self.events: list[ProcessorEvent] = []

    def task_started(self, task: Task) -> None:
        self.events.append(("task_started", task, None, None))

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.events.append(("task_completed", task, None, result))

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("task_instance_started", task, host, None))

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("task_instance_completed", task, host, result))

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("subtask_instance_started", task, host, None))

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("subtask_instance_completed", task, host, result))


class OrderingProcessor:
    def __init__(self, label: str, events: list[tuple[str, str]]) -> None:
        self.label = label
        self.events = events

    def _record(self, event: str) -> None:
        self.events.append((event, self.label))

    def task_started(self, task: Task) -> None:
        self._record("task_started")

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self._record("task_completed")

    def task_instance_started(self, task: Task, host: Host) -> None:
        self._record("task_instance_started")

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self._record("task_instance_completed")

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self._record("subtask_instance_started")

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self._record("subtask_instance_completed")


class StructuralAsyncRunner:
    """Small deterministic runner proving that Nornir uses the structural contract."""

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        raise RunnerNotSyncError(type(self).__name__)

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        result = AggregatedResult(task.name)
        for host in hosts:
            result[host.name] = await task.copy().astart(host)
        return result


class SyncArunRunner:
    def __init__(self) -> None:
        self.called = False

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        raise AssertionError("sync run is not expected")

    def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        self.called = True
        return AggregatedResult(task.name)


class InventoryFixture:
    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs

    def load(self) -> Inventory:
        return make_inventory("configured")


class AsyncCallable:
    async def __call__(self, task: Task, value: str) -> Result:
        await asyncio.sleep(0)
        return Result(host=task.host, result=f"{task.host.name}:{value}")


class SyncCallable:
    def __call__(self, task: Task) -> None:
        raise AssertionError("a mismatched task must not execute")


class CleanupLegacyPlugin:
    instances: ClassVar[list[CleanupLegacyPlugin]] = []

    def __init__(self) -> None:
        self.closed = 0
        self._connection = object()
        self.__class__.instances.append(self)

    @property
    def connection(self) -> object:
        return self._connection

    def open(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        pass

    def close(self) -> None:
        self.closed += 1


class CleanupSyncPlugin(CleanupLegacyPlugin):
    instances: ClassVar[list[Any]] = []

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync"})


class CleanupAsyncPlugin:
    instances: ClassVar[list[CleanupAsyncPlugin]] = []
    fail_close: ClassVar[bool] = False

    def __init__(self) -> None:
        self.closed = 0
        self._connection = object()
        self.__class__.instances.append(self)

    @property
    def connection(self) -> object:
        return self._connection

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})

    async def aopen(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        await asyncio.sleep(0)

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        if self.fail_close:
            raise RuntimeError("async cleanup failed")
        self.closed += 1


class CleanupDualPlugin(CleanupSyncPlugin):
    instances: ClassVar[list[Any]] = []

    def __init__(self) -> None:
        super().__init__()
        self.async_closed = 0

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync", "asyncio"})

    async def aopen(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        await asyncio.sleep(0)

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        self.async_closed += 1


@pytest.fixture
def cleanup_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(ConnectionPluginRegister.available, "cleanup-legacy", CleanupLegacyPlugin)
    monkeypatch.setitem(
        CapabilityConnectionPluginRegister.available,
        "cleanup-sync",
        CleanupSyncPlugin,
    )
    monkeypatch.setitem(
        CapabilityConnectionPluginRegister.available,
        "cleanup-async",
        CleanupAsyncPlugin,
    )
    monkeypatch.setitem(
        CapabilityConnectionPluginRegister.available,
        "cleanup-dual",
        CleanupDualPlugin,
    )
    for plugin in (
        CleanupLegacyPlugin,
        CleanupSyncPlugin,
        CleanupAsyncPlugin,
        CleanupDualPlugin,
    ):
        plugin.instances.clear()
    CleanupAsyncPlugin.fail_close = False


def make_inventory(*hostnames: str) -> Inventory:
    return Inventory(
        hosts=Hosts({hostname: Host(hostname) for hostname in hostnames}),
        groups=Groups(),
        defaults=Defaults(),
    )


def make_nornir(
    *hostnames: str,
    processor: RecordingProcessor | None = None,
    runner: Any | None = None,
    raise_on_error: bool = False,
) -> Nornir:
    processors = Processors([processor]) if processor is not None else Processors()
    return Nornir(
        inventory=make_inventory(*hostnames),
        config=Config(core=CoreConfig(raise_on_error=raise_on_error)),
        processors=processors,
        runner=runner if runner is not None else AsyncioRunner(),
    )


async def result_task(task: Task, prefix: str, changed: bool = False) -> Result:
    await asyncio.sleep(0)
    return Result(host=task.host, result=f"{prefix}:{task.host.name}", changed=changed)


async def failing_task(task: Task, fail_on: set[str]) -> str:
    await asyncio.sleep(0)
    if task.host.name in fail_on:
        raise ValueError(f"failed {task.host.name}")
    return task.host.name


async def named_partial_target(task: Task, prefix: str) -> str:
    await asyncio.sleep(0)
    return f"{prefix}:{task.host.name}"


def sync_task(task: Task) -> None:
    raise AssertionError("a mismatched task must not execute")


async def async_task(task: Task) -> str:
    await asyncio.sleep(0)
    return task.host.name


def assert_no_host_events(processor: RecordingProcessor) -> None:
    assert all(event[2] is None for event in processor.events)


def test_arun_has_the_documented_coroutine_signature() -> None:
    signature = inspect.signature(Nornir.arun)

    assert inspect.iscoroutinefunction(Nornir.arun)
    assert list(signature.parameters) == [
        "self",
        "task",
        "raise_on_error",
        "on_good",
        "on_failed",
        "name",
        "kwargs",
    ]
    assert signature.parameters["raise_on_error"].default is None
    assert signature.parameters["on_good"].default is True
    assert signature.parameters["on_failed"].default is False
    assert signature.parameters["name"].default is None
    assert signature.parameters["kwargs"].kind is inspect.Parameter.VAR_KEYWORD


def test_arun_returns_aggregate_and_preserves_task_arguments_and_events() -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir("first", "second", processor=processor)

        result = await nr.arun(
            result_task,
            name="named operation",
            prefix="value",
            changed=True,
        )

        assert isinstance(result, AggregatedResult)
        assert result.name == "named operation"
        assert list(result) == ["first", "second"]
        assert [host_result[0].result for host_result in result.values()] == [
            "value:first",
            "value:second",
        ]
        assert all(host_result[0].changed for host_result in result.values())

        events = processor.events
        assert events[0][0] == "task_started"
        assert events[-1][0] == "task_completed"
        assert [event[0] for event in events].count("task_instance_started") == 2
        assert [event[0] for event in events].count("task_instance_completed") == 2
        run_task = events[0][1]
        assert run_task.name == "named operation"
        assert run_task.task is result_task
        assert run_task.params == {"prefix": "value", "changed": True}
        assert events[-1][1] is run_task
        assert events[-1][3] is result

        for hostname in result:
            started = next(
                event
                for event in events
                if event[0] == "task_instance_started"
                and event[2] is not None
                and event[2].name == hostname
            )
            completed = next(
                event
                for event in events
                if event[0] == "task_instance_completed"
                and event[2] is not None
                and event[2].name == hostname
            )
            assert events.index(started) < events.index(completed)
            assert started[1].name == "named operation"
            assert completed[1] is started[1]
            assert completed[2] is started[2]
            assert completed[3] is result[hostname]

    asyncio.run(exercise())


def test_arun_accepts_a_structural_async_runner() -> None:
    async def exercise() -> None:
        nr = make_nornir("host", runner=StructuralAsyncRunner())
        result = await nr.arun(async_task)
        assert result["host"].result == "host"

    asyncio.run(exercise())


def test_arun_calls_processors_in_configured_order_for_each_event() -> None:
    async def exercise() -> None:
        events: list[tuple[str, str]] = []
        first = OrderingProcessor("first", events)
        second = OrderingProcessor("second", events)
        nr = Nornir(
            inventory=make_inventory("host"),
            processors=Processors([first, second]),
            runner=AsyncioRunner(),
        )

        await nr.arun(async_task)

        assert events == [
            ("task_started", "first"),
            ("task_started", "second"),
            ("task_instance_started", "first"),
            ("task_instance_started", "second"),
            ("task_instance_completed", "first"),
            ("task_instance_completed", "second"),
            ("task_completed", "first"),
            ("task_completed", "second"),
        ]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "task",
    [functools.partial(named_partial_target, prefix="partial"), AsyncCallable()],
)
def test_arun_accepts_named_partial_and_async_callable_tasks(task: AsyncTask) -> None:
    async def exercise() -> None:
        if isinstance(task, AsyncCallable):
            result = await make_nornir("host").arun(
                task,
                name="explicit",
                value="callable",
            )
        else:
            result = await make_nornir("host").arun(task, name="explicit")
        assert result.name == "explicit"
        assert result["host"].name == "explicit"

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("on_good", "on_failed", "expected"),
    [
        (True, False, ["good-1", "good-2"]),
        (False, True, ["failed"]),
        (True, True, ["good-1", "good-2", "failed"]),
        (False, False, []),
    ],
)
def test_arun_selects_good_then_failed_hosts(
    on_good: bool, on_failed: bool, expected: list[str]
) -> None:
    async def exercise() -> None:
        nr = make_nornir("good-1", "failed", "good-2")
        nr.data.failed_hosts.add("failed")

        result = await nr.arun(async_task, on_good=on_good, on_failed=on_failed)

        assert list(result) == expected

    asyncio.run(exercise())


def test_arun_reuses_failed_hosts_and_skips_them_by_default() -> None:
    async def exercise() -> None:
        nr = make_nornir("good", "bad")

        first = await nr.arun(failing_task, fail_on={"bad"})
        second = await nr.arun(failing_task, fail_on=set())
        retry = await nr.arun(
            failing_task,
            fail_on=set(),
            on_good=False,
            on_failed=True,
        )

        assert set(first.failed_hosts) == {"bad"}
        assert nr.data.failed_hosts == {"bad"}
        assert list(second) == ["good"]
        assert list(retry) == ["bad"]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("configured", "override", "raises"),
    [
        (False, None, False),
        (True, None, True),
        (False, True, True),
        (True, False, False),
    ],
)
def test_arun_resolves_raise_on_error(
    configured: bool, override: bool | None, raises: bool
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir(
            "bad",
            processor=processor,
            raise_on_error=configured,
        )

        if raises:
            with pytest.raises(NornirExecutionError) as error:
                await nr.arun(failing_task, raise_on_error=override, fail_on={"bad"})
            assert set(error.value.result.failed_hosts) == {"bad"}
            assert nr.data.failed_hosts == set()
            assert [event[0] for event in processor.events][-1] == "task_instance_completed"
        else:
            result = await nr.arun(failing_task, raise_on_error=override, fail_on={"bad"})
            assert set(result.failed_hosts) == {"bad"}
            assert nr.data.failed_hosts == {"bad"}
            assert processor.events[-1] == ("task_completed", processor.events[0][1], None, result)

    asyncio.run(exercise())


def test_arun_warns_when_no_hosts_are_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    warnings: list[tuple[str, str]] = []

    def record_warning(message: str, task_name: str) -> None:
        warnings.append((message, task_name))

    monkeypatch.setattr("nornir.core.logger.warning", record_warning)

    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir("failed", processor=processor)
        nr.data.failed_hosts.add("failed")

        result = await nr.arun(async_task)

        assert not result
        assert warnings[0][0].startswith("Task %r has not been run")
        assert warnings[0][1] == "async_task"
        assert [event[0] for event in processor.events] == ["task_started", "task_completed"]

    asyncio.run(exercise())


def test_asyncio_runner_is_selected_by_configuration_and_with_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(InventoryPluginRegister.available, "async-run-inventory", InventoryFixture)
    monkeypatch.setitem(RunnersPluginRegister.available, "asyncio", AsyncioRunner)

    configured = InitNornir(
        inventory={"plugin": "async-run-inventory"},
        runner={"plugin": "asyncio", "options": {"num_workers": 7}},
        logging={"enabled": False},
    )
    processor = RecordingProcessor()
    original = make_nornir("original", processor=processor, runner=SerialRunner())
    replacement = AsyncioRunner(num_workers=3)
    cloned = original.with_runner(replacement)

    assert isinstance(configured.runner, AsyncioRunner)
    assert configured.runner.num_workers == 7
    assert configured.config.runner.plugin == "asyncio"
    assert configured.config.runner.options == {"num_workers": 7}
    assert cloned.runner is replacement
    assert original.runner is not replacement
    assert cloned.inventory is original.inventory
    assert cloned.config is original.config
    assert cloned.data is original.data
    assert cloned.processors is original.processors


@pytest.mark.parametrize(
    ("task", "name", "expected_name"),
    [
        (sync_task, None, "sync_task"),
        (functools.partial(sync_task), None, "partial"),
        (SyncCallable(), None, "SyncCallable"),
        (SyncCallable(), "safe explicit name", "safe explicit name"),
    ],
)
def test_arun_rejects_sync_tasks_before_preparation(
    task: Callable[..., Any], name: str | None, expected_name: str
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir("host", processor=processor)

        with pytest.raises(SyncTaskOnAsyncRunError) as error:
            await nr.arun(task, name=name)

        assert error.value.task_name == expected_name
        message = str(error.value)
        assert expected_name in message
        assert "async def" in message
        assert "synchronous runner" in message
        assert SYNC_TASKS_IN_ASYNC_RUNS_ISSUE in message
        assert processor.events == []

    asyncio.run(exercise())


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner(num_workers=2)])
@pytest.mark.parametrize(
    ("task", "expected_name"),
    [
        (async_task, "async_task"),
        (functools.partial(async_task), "partial"),
        (AsyncCallable(), "AsyncCallable"),
    ],
)
def test_run_rejects_async_tasks_before_preparation(
    runner: Any, task: Callable[..., Any], expected_name: str
) -> None:
    processor = RecordingProcessor()
    nr = make_nornir("host", processor=processor, runner=runner)

    with pytest.raises(AsyncTaskOnSyncRunError) as error:
        nr.run(task)

    assert error.value.task_name == expected_name
    message = str(error.value)
    assert expected_name in message
    assert "await nr.arun" in message
    assert "await task.arun" in message
    assert "synchronous task" in message
    assert processor.events == []


def test_arun_checks_task_kind_before_runner_compatibility() -> None:
    processor = RecordingProcessor()
    nr = make_nornir("host", processor=processor, runner=SerialRunner())

    async def exercise() -> None:
        with pytest.raises(SyncTaskOnAsyncRunError):
            await nr.arun(cast("AsyncTask", sync_task))

    asyncio.run(exercise())
    assert processor.events == []


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner(num_workers=2)])
def test_arun_rejects_sync_runners_before_preparation(runner: Any) -> None:
    processor = RecordingProcessor()
    nr = make_nornir("host", processor=processor, runner=runner)

    async def exercise() -> None:
        with pytest.raises(RunnerNotAsyncError) as error:
            await nr.arun(async_task)

        assert error.value.runner_name == type(runner).__name__
        message = str(error.value)
        assert "nr.run" in message
        assert "nr.close_connections" in message
        assert "with nr" in message
        assert "asyncio runner" in message

    asyncio.run(exercise())
    assert processor.events == []


def test_arun_rejects_a_runner_with_synchronous_arun() -> None:
    processor = RecordingProcessor()
    runner = SyncArunRunner()
    nr = make_nornir("host", processor=processor, runner=runner)

    async def exercise() -> None:
        with pytest.raises(RunnerNotAsyncError) as error:
            await nr.arun(async_task)
        assert error.value.runner_name == "SyncArunRunner"

    asyncio.run(exercise())
    assert not runner.called
    assert processor.events == []


def test_sync_run_with_asyncio_runner_emits_only_global_start() -> None:
    processor = RecordingProcessor()
    nr = make_nornir("host", processor=processor, runner=AsyncioRunner())

    with pytest.raises(RunnerNotSyncError) as error:
        nr.run(sync_task)

    assert error.value.runner_name == "AsyncioRunner"
    assert "await nr.arun" in str(error.value)
    assert [event[0] for event in processor.events] == ["task_started"]
    assert_no_host_events(processor)


def test_async_cleanup_has_the_documented_signatures() -> None:
    close_signature = inspect.signature(Nornir.aclose_connections)
    exit_signature = inspect.signature(Nornir.__aexit__)

    assert inspect.iscoroutinefunction(Nornir.aclose_connections)
    assert list(close_signature.parameters) == ["self", "on_good", "on_failed"]
    assert close_signature.parameters["on_good"].default is True
    assert close_signature.parameters["on_failed"].default is False
    assert close_signature.return_annotation == "None"
    assert inspect.iscoroutinefunction(Nornir.__aenter__)
    assert inspect.iscoroutinefunction(Nornir.__aexit__)
    assert list(exit_signature.parameters) == ["self", "exc_type", "exc_value", "traceback"]


def test_async_context_closes_mixed_connections_on_good_and_failed_hosts(
    cleanup_plugins: None,
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir("good", "failed", processor=processor)
        nr.data.failed_hosts.add("failed")

        for host in nr.inventory.hosts.values():
            host.get_connection("cleanup-legacy", nr.config)
            host.get_connection("cleanup-sync", nr.config)
            await host.aget_connection("cleanup-async", nr.config)
            host.get_connection("cleanup-dual", nr.config)

        async with nr as entered:
            assert entered is nr

        assert all(plugin.closed == 1 for plugin in CleanupLegacyPlugin.instances)
        assert all(plugin.closed == 1 for plugin in CleanupSyncPlugin.instances)
        assert all(plugin.closed == 1 for plugin in CleanupAsyncPlugin.instances)
        assert all(plugin.async_closed == 1 for plugin in CleanupDualPlugin.instances)
        assert all(plugin.closed == 0 for plugin in CleanupDualPlugin.instances)
        for host in nr.inventory.hosts.values():
            assert host.connections == {}
            assert host._async_connections == {}
            assert host._capability_connections == {}

        event_names = [event[0] for event in processor.events]
        assert event_names[0] == "task_started"
        assert event_names[-1] == "task_completed"
        assert event_names.count("task_instance_started") == 2
        assert event_names.count("task_instance_completed") == 2
        assert processor.events[0][1].name == "close_connections_task"

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("on_good", "on_failed", "closed_hosts"),
    [
        (True, False, {"good"}),
        (False, True, {"failed"}),
        (True, True, {"good", "failed"}),
        (False, False, set()),
    ],
)
def test_aclose_connections_selects_good_and_failed_hosts(
    cleanup_plugins: None,
    on_good: bool,
    on_failed: bool,
    closed_hosts: set[str],
) -> None:
    async def exercise() -> None:
        nr = make_nornir("good", "failed")
        nr.data.failed_hosts.add("failed")
        plugins: dict[str, CleanupAsyncPlugin] = {}
        for hostname, host in nr.inventory.hosts.items():
            await host.aget_connection("cleanup-async", nr.config)
            plugins[hostname] = CleanupAsyncPlugin.instances[-1]

        await nr.aclose_connections(on_good=on_good, on_failed=on_failed)

        for hostname, host in nr.inventory.hosts.items():
            assert plugins[hostname].closed == (hostname in closed_hosts)
            assert ("cleanup-async" in host._async_connections) == (
                hostname not in closed_hosts
            )

    asyncio.run(exercise())


def test_sync_cleanup_and_context_reject_asyncio_runner() -> None:
    nr = make_nornir("host")

    with pytest.raises(RunnerNotSyncError) as cleanup_error:
        nr.close_connections()
    assert cleanup_error.value.runner_name == "AsyncioRunner"
    assert "await nr.aclose_connections" in str(cleanup_error.value)

    with pytest.raises(RunnerNotSyncError) as context_error, nr:
        pass
    assert context_error.value.runner_name == "AsyncioRunner"
    assert "async with nr" in str(context_error.value)


def test_async_cleanup_and_context_reject_serial_runner() -> None:
    async def exercise() -> None:
        nr = make_nornir("host", runner=SerialRunner())

        with pytest.raises(RunnerNotAsyncError) as cleanup_error:
            await nr.aclose_connections()
        assert cleanup_error.value.runner_name == "SerialRunner"
        assert "nr.close_connections" in str(cleanup_error.value)

        with pytest.raises(RunnerNotAsyncError) as context_error:
            async with nr:
                pass
        assert context_error.value.runner_name == "SerialRunner"
        assert "with nr" in str(context_error.value)

    asyncio.run(exercise())


def test_failed_async_cleanup_is_bookkept_and_retryable_on_failed_hosts(
    cleanup_plugins: None,
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir("host", processor=processor)
        host = nr.inventory.hosts["host"]
        await host.aget_connection("cleanup-async", nr.config)
        plugin = CleanupAsyncPlugin.instances[0]
        CleanupAsyncPlugin.fail_close = True

        assert host.connections == {}
        await nr.aclose_connections()

        assert nr.data.failed_hosts == {"host"}
        assert host.connections == {}
        assert host._async_connections == {"cleanup-async": plugin}
        assert host._capability_connections.keys() == {"cleanup-async"}

        CleanupAsyncPlugin.fail_close = False
        await nr.aclose_connections()
        assert plugin.closed == 0
        assert host._async_connections == {"cleanup-async": plugin}

        await nr.aclose_connections(on_good=False, on_failed=True)
        assert plugin.closed == 1
        assert host._async_connections == {}
        assert host._capability_connections == {}
        assert [event[0] for event in processor.events].count("task_completed") == 3

    asyncio.run(exercise())


def test_failed_async_cleanup_propagates_when_raise_on_error_is_enabled(
    cleanup_plugins: None,
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        nr = make_nornir(
            "host",
            processor=processor,
            raise_on_error=True,
        )
        host = nr.inventory.hosts["host"]
        await host.aget_connection("cleanup-async", nr.config)
        plugin = CleanupAsyncPlugin.instances[0]
        CleanupAsyncPlugin.fail_close = True

        with pytest.raises(NornirExecutionError) as error:
            await nr.aclose_connections()

        assert set(error.value.result.failed_hosts) == {"host"}
        assert nr.data.failed_hosts == set()
        assert host.connections == {}
        assert host._async_connections == {"cleanup-async": plugin}
        assert [event[0] for event in processor.events][-1] == "task_instance_completed"

    asyncio.run(exercise())
