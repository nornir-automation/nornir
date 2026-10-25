from __future__ import annotations

import pickle  # noqa: S403 - round trips of the errors defined by nornir
import time
import traceback
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    OperationAlreadyRegisteredError,
    OperationConnectionNotSetError,
    OperationContractNotFoundError,
    OperationEntryPointError,
    OperationError,
    OperationInputError,
    OperationNotRegisteredError,
    OperationOutputError,
    RunnerCapabilityError,
    RunnerNotSyncError,
    TaskCancelledError,
    TaskTimeoutError,
)
from nornir.core.operations import Operation, OperationRegistry
from nornir.core.run import RunOptions
from nornir.core.task import PartialResult, Result, Task
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.operations_helpers import (
    Backup,
    BackupInput,
    BackupOutput,
    GetConfig,
    GetConfigInput,
    GetConfigOutput,
    aios_get_config,
    backup_task,
    make_nornir,
    register_get_config,
)
from tests.core.run_helpers import EventLog

if TYPE_CHECKING:
    from collections.abc import Generator

    from nornir.core.inventory import Host
    from nornir.core.plugins.runners import RunnerPlugin
    from nornir.core.task import AggregatedResult

pytestmark = pytest.mark.usefixtures("operation_registry")

RUNNERS = [SerialRunner(), ThreadedRunner(num_workers=2)]


def outputs(results: list[Result[GetConfigOutput]]) -> dict[str, str]:
    return {r.host.name: r.result.config for r in results if r.host is not None}


def errors(result: AggregatedResult) -> dict[str, BaseException | None]:
    return {name: r[0].exception for name, r in result.items()}


# --- User Story 1: run one Operation across vendors ----------------------------------


@pytest.mark.parametrize("runner", RUNNERS)
def test_each_host_runs_the_task_of_its_platform(runner: RunnerPlugin) -> None:
    register_get_config()
    nr = make_nornir(runner)

    stream = nr.run_operation(GetConfig, connection="napalm", params=GetConfigInput())
    results = list(stream.results())

    assert outputs(results) == {
        "r1": "ios running r1",
        "r2": "eos running r2",
        "r3": "junos running r3",
    }
    assert all(isinstance(r.result, GetConfigOutput) for r in results)
    assert all(r.name == "get_config" for r in results)
    assert not stream.result().failed


def test_iterating_the_stream_yields_results_and_partial_results() -> None:
    def progress_get_config(
        task: Task, params: GetConfigInput
    ) -> Generator[PartialResult, None, GetConfigOutput]:
        yield PartialResult(task.host, "fetching", progress=0.5)
        return GetConfigOutput(config="ios")  # noqa: B901 - a progress task returns its output

    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=progress_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    events = list(nr.run_operation(GetConfig, connection="napalm"))

    assert [type(e).__name__ for e in events] == ["PartialResult", "Result"]
    final = events[-1]
    assert isinstance(final, Result)
    assert final.result == GetConfigOutput(config="ios")


def test_params_none_builds_the_default_input() -> None:
    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(nr.run_operation(GetConfig, connection="napalm").results())

    assert outputs(results) == {"r1": "ios running r1"}


def test_params_as_a_mapping() -> None:
    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(
        nr.run_operation(GetConfig, {"retrieve": "startup"}, connection="napalm").results()
    )

    assert outputs(results) == {"r1": "ios startup r1"}


def test_operation_given_by_name() -> None:
    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(nr.run_operation("get_config", connection="napalm").results())

    assert results[0].result == GetConfigOutput(config="ios running r1")


def test_unknown_operation_name_raises_before_the_run() -> None:
    log = EventLog()
    nr = make_nornir(SerialRunner(), processors=[log])

    with pytest.raises(OperationContractNotFoundError) as info:
        nr.run_operation("get_cfg", connection="napalm")

    assert "'get_cfg'" in str(info.value)
    assert "get_config" in str(info.value)
    assert log.events == []


def test_connection_comes_from_the_configuration() -> None:
    register_get_config(connection="netmiko")
    nr = make_nornir(SerialRunner(), {"r1": "ios"}, operation_connection="netmiko")

    results = list(nr.run_operation(GetConfig).results())

    assert outputs(results) == {"r1": "ios running r1"}


def test_connection_argument_overrides_the_configuration() -> None:
    register_get_config(connection="napalm")
    nr = make_nornir(SerialRunner(), {"r1": "ios"}, operation_connection="netmiko")

    results = list(nr.run_operation(GetConfig, connection="napalm").results())

    assert outputs(results) == {"r1": "ios running r1"}


def test_connection_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NORNIR_CORE_OPERATION_CONNECTION", "napalm")
    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    assert nr.config.core.operation_connection == "napalm"
    assert nr.config.core.dict() == {"raise_on_error": False, "operation_connection": "napalm"}
    assert outputs(list(nr.run_operation(GetConfig).results())) == {"r1": "ios running r1"}


def test_no_connection_raises_before_the_run() -> None:
    register_get_config()
    log = EventLog()
    nr = make_nornir(SerialRunner(), processors=[log])

    with pytest.raises(OperationConnectionNotSetError, match="'get_config'"):
        nr.run_operation(GetConfig)

    assert log.events == []


def test_submit_operation_returns_a_handle() -> None:
    register_get_config()
    nr = make_nornir(ThreadedRunner(num_workers=2))

    handle = nr.submit_operation(GetConfig, connection="napalm")

    assert outputs(list(handle.results())) == {
        "r1": "ios running r1",
        "r2": "eos running r2",
        "r3": "junos running r3",
    }
    assert not handle.result(timeout=10).failed


def test_submit_operation_on_serial_runner_raises() -> None:
    register_get_config()
    nr = make_nornir(SerialRunner())

    with pytest.raises(RunnerCapabilityError, match="submit_operation"):
        nr.submit_operation(GetConfig, connection="napalm")


def test_run_operation_on_an_asynchronous_runner_raises() -> None:
    register_get_config()
    nr = make_nornir(AsyncioRunner())

    with pytest.raises(RunnerNotSyncError):
        nr.run_operation(GetConfig, connection="napalm")


@pytest.mark.parametrize("runner", RUNNERS)
def test_host_with_unregistered_platform_or_no_platform_fails_alone(
    runner: RunnerPlugin,
) -> None:
    register_get_config()
    nr = make_nornir(runner, {"r1": "ios", "fw1": "panos", "x1": None})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    found = errors(result)
    assert found["r1"] is None
    panos = found["fw1"]
    assert isinstance(panos, OperationNotRegisteredError)
    assert panos.platform == "panos"
    assert panos.host_name == "fw1"
    assert str(panos) == (
        "no task registered for operation 'get_config' on platform 'panos' with connection "
        "'napalm' (host 'fw1'). Registered for 'get_config': eos.napalm, ios.napalm, "
        "junos.napalm."
    )
    no_platform = found["x1"]
    assert isinstance(no_platform, OperationNotRegisteredError)
    assert no_platform.platform is None
    assert str(no_platform) == (
        "host 'x1' has no platform, so no task can be selected for operation 'get_config'."
    )
    assert nr.data.failed_hosts == {"fw1", "x1"}


@pytest.mark.parametrize("runner", RUNNERS)
def test_output_of_the_wrong_type_fails_the_host(runner: RunnerPlugin) -> None:
    def dict_get_config(task: Task, params: GetConfigInput) -> dict[str, str]:
        return {"config": "ios"}

    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=dict_get_config
    )
    nr = make_nornir(runner, {"r1": "ios"})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    error = result["r1"][0].exception
    assert isinstance(error, OperationOutputError)
    assert str(error) == (
        "task 'dict_get_config' for operation 'get_config' on host 'r1' returned 'dict', "
        "expected 'GetConfigOutput'."
    )
    assert result["r1"][0].failed


def test_invalid_static_input_raises_before_the_run() -> None:
    calls: list[str] = []

    def spy(task: Task, params: GetConfigInput) -> GetConfigOutput:
        calls.append(task.host.name)
        return GetConfigOutput(config="")

    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=spy
    )
    log = EventLog()
    nr = make_nornir(SerialRunner(), {"r1": "ios"}, processors=[log])

    with pytest.raises(OperationInputError) as info:
        nr.run_operation(GetConfig, {"sanitize": True}, connection="napalm")

    assert str(info.value) == (
        "invalid input for operation 'get_config': unexpected field 'sanitize' "
        "(did you mean 'sanitized'?)"
    )
    assert isinstance(info.value.__cause__, TypeError)
    assert calls == []
    assert log.events == []


def test_input_of_another_type_raises() -> None:
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    with pytest.raises(OperationInputError, match="expected GetConfigInput"):
        nr.run_operation(GetConfig, 42, connection="napalm")  # type: ignore[arg-type]


class ValidatingInput:
    """A model with ``model_validate``, as Pydantic models have."""

    def __init__(self, retrieve: str) -> None:
        self.retrieve = retrieve

    @classmethod
    def model_validate(cls, value: Any) -> ValidatingInput:
        if not isinstance(value, dict) or not isinstance(value.get("retrieve"), str):
            msg = "retrieve must be a string"
            raise ValueError(msg)
        return cls(value["retrieve"])


class Validated(Operation[ValidatingInput, GetConfigOutput]):
    name = "validated"


def test_input_model_with_model_validate() -> None:
    def task(task: Task, params: ValidatingInput) -> GetConfigOutput:
        return GetConfigOutput(config=params.retrieve)

    OperationRegistry.register(operation="validated", platform="ios", connection="c", task=task)
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(nr.run_operation(Validated, {"retrieve": "x"}, connection="c").results())
    assert outputs(results) == {"r1": "x"}

    with pytest.raises(OperationInputError, match="ValueError: retrieve must be a string"):
        nr.run_operation(Validated, {"retrieve": 3}, connection="c")


@pytest.mark.parametrize("runner", RUNNERS)
def test_asynchronous_task_on_a_synchronous_run_fails_the_host(runner: RunnerPlugin) -> None:
    register_get_config()
    OperationRegistry.register(
        operation="get_config",
        platform="ios",
        connection="napalm",
        task=aios_get_config,
        replace=True,
    )
    nr = make_nornir(runner)

    result = nr.run_operation(GetConfig, connection="napalm").result()

    found = errors(result)
    assert isinstance(found["r1"], AsyncTaskOnSyncRunError)
    assert str(found["r1"]).startswith(
        "Task 'aios_get_config' (selected for operation 'get_config' on host 'r1') is "
        "asynchronous and cannot run synchronously."
    )
    assert found["r2"] is None
    assert found["r3"] is None


def raising_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    msg = "device unreachable"
    raise ConnectionError(msg)


def test_traceback_has_the_same_frames_as_a_plain_task() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=raising_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    operation_error = nr.run_operation(GetConfig, connection="napalm").result()["r1"][0].exception
    plain_nr = make_nornir(SerialRunner(), {"r1": "ios"})
    plain_error = plain_nr.run(raising_get_config, params=GetConfigInput())["r1"][0].exception

    assert isinstance(operation_error, ConnectionError)
    assert isinstance(plain_error, ConnectionError)
    operation_frames = traceback.extract_tb(operation_error.__traceback__)
    plain_frames = traceback.extract_tb(plain_error.__traceback__)
    assert [f.name for f in operation_frames] == [f.name for f in plain_frames]
    assert operation_frames[-1].name == "raising_get_config"


def test_processors_see_the_operation_name_and_the_selected_task() -> None:
    seen: list[tuple[str, str]] = []

    class Recorder(EventLog):
        def task_instance_completed(self, task: Task, host: Host, result: Any) -> None:
            seen.append((task.name, task.task.__name__))

    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"}, processors=[Recorder()])

    nr.run_operation(GetConfig, connection="napalm").result()

    assert seen == [("get_config", "ios_get_config")]


def test_cancel_and_checkpoint_inside_an_implementation() -> None:
    def slow_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
        for _ in range(50):
            task.checkpoint()
            time.sleep(0.01)
        return GetConfigOutput(config="slow")

    for platform in ("ios", "eos", "junos"):
        OperationRegistry.register(
            operation="get_config", platform=platform, connection="napalm", task=slow_get_config
        )
    nr = make_nornir(SerialRunner())

    stream = nr.run_operation(GetConfig, connection="napalm")
    stream.cancel()
    result = stream.result()

    assert all(isinstance(e, TaskCancelledError) for e in errors(result).values())


def test_per_host_timeout_applies_to_an_implementation() -> None:
    def slow_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
        for _ in range(200):
            task.checkpoint()
            time.sleep(0.01)
        return GetConfigOutput(config="slow")

    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=slow_get_config
    )
    nr = make_nornir(ThreadedRunner(num_workers=1), {"r1": "ios"})

    result = nr.run_operation(
        GetConfig, connection="napalm", run_options=RunOptions(per_host_timeout=0.1)
    ).result()

    assert isinstance(result["r1"][0].exception, TaskTimeoutError)


def test_implementation_is_a_plain_task() -> None:
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    result = nr.run(task=backup_task, params=BackupInput(path="/tmp/r1"))  # noqa: S108

    assert result["r1"][0].result == BackupOutput(written="/tmp/r1")  # noqa: S108


def test_operation_errors_pickle() -> None:
    samples: list[OperationError] = [
        OperationInputError("op", "bad", "r1"),
        OperationOutputError("op", "t", "dict", "Out", "r1"),
        OperationNotRegisteredError("op", "ios", "napalm", ("eos.napalm",), "r1"),
        OperationNotRegisteredError("op", None, "napalm", host_name="r1"),
        OperationAlreadyRegisteredError("op", "op.ios.napalm", "a", "b"),
        OperationAlreadyRegisteredError("op", None, "a", "b"),
        OperationConnectionNotSetError("op"),
        OperationEntryPointError("op", "dist", "op.ios", "bad name"),
        OperationContractNotFoundError("op", ("a", "b")),
    ]
    for error in samples:
        copy = pickle.loads(pickle.dumps(error))  # noqa: S301 - round trip of our own object
        assert type(copy) is type(error)
        assert str(copy) == str(error)
        assert copy.operation == "op"


# --- User Story 2: report a change -----------------------------------------------------


def test_result_with_changed_and_diff_is_kept() -> None:
    def apply_backup(task: Task, params: BackupInput) -> Result[BackupOutput]:
        return Result(
            task.host,
            result=BackupOutput(written=params.path),
            changed=True,
            diff="+ line",
            severity_level=30,
        )

    OperationRegistry.register(
        operation="backup", platform="ios", connection="c", task=apply_backup
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(nr.run_operation(Backup, BackupInput(path="/b"), connection="c").results())

    assert len(results) == 1
    res = results[0]
    assert res.changed is True
    assert res.diff == "+ line"
    assert res.severity_level == 30
    assert res.result.written == "/b"


def test_failed_result_is_not_checked_against_the_output_model() -> None:
    error = RuntimeError("refused")

    def refuse(task: Task, params: BackupInput) -> Result[BackupOutput]:
        return Result(task.host, failed=True, exception=error)

    OperationRegistry.register(operation="backup", platform="ios", connection="c", task=refuse)
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    result = nr.run_operation(Backup, {"path": "/b"}, connection="c").result()

    assert result["r1"][0].failed
    assert result["r1"][0].exception is error


def test_result_holding_the_wrong_type_fails_and_keeps_changed() -> None:
    def wrong(task: Task, params: BackupInput) -> Result[Any]:
        return Result(task.host, result="written", changed=True, diff="d")

    OperationRegistry.register(operation="backup", platform="ios", connection="c", task=wrong)
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    res = nr.run_operation(Backup, {"path": "/b"}, connection="c").result()["r1"][0]

    assert isinstance(res.exception, OperationOutputError)
    assert res.exception.returned_type == "str"
    assert res.changed is True
    assert res.diff == "d"


# --- User Story 3: parameters for each host --------------------------------------------


@pytest.mark.parametrize("runner", RUNNERS)
def test_params_callable_builds_one_input_per_host(runner: RunnerPlugin) -> None:
    for platform in ("ios", "eos"):
        OperationRegistry.register(
            operation="backup", platform=platform, connection="c", task=backup_task
        )
    nr = make_nornir(runner, {"r1": "ios", "r2": "eos"})

    results = nr.run_operation(
        Backup, lambda host: BackupInput(path=f"/backup/{host.name}"), connection="c"
    ).results()

    assert {r.host.name: r.result.written for r in results if r.host} == {
        "r1": "/backup/r1",
        "r2": "/backup/r2",
    }


def test_params_callable_may_return_a_mapping() -> None:
    OperationRegistry.register(operation="backup", platform="ios", connection="c", task=backup_task)
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(
        nr.run_operation("backup", lambda host: {"path": host.name}, connection="c").results()
    )

    assert results[0].result == BackupOutput(written="r1")


def test_params_callable_that_raises_fails_only_that_host() -> None:
    OperationRegistry.register(operation="backup", platform="ios", connection="c", task=backup_task)
    nr = make_nornir(SerialRunner(), {"r1": "ios", "r2": "ios"})

    def params(host: Host) -> BackupInput:
        if host.name == "r2":
            return BackupInput(path=host.data["path"])
        return BackupInput(path="/r1")

    result = nr.run_operation(Backup, params, connection="c").result()

    assert result["r1"][0].exception is None
    error = result["r2"][0].exception
    assert isinstance(error, OperationInputError)
    assert error.host_name == "r2"
    assert str(error) == (
        "invalid input for operation 'backup' on host 'r2': the params callable raised "
        "KeyError('path')"
    )
    assert isinstance(error.__cause__, KeyError)


def test_params_callable_that_returns_an_invalid_input_fails_only_that_host() -> None:
    OperationRegistry.register(operation="backup", platform="ios", connection="c", task=backup_task)
    nr = make_nornir(SerialRunner(), {"r1": "ios", "r2": "ios"})

    result = nr.run_operation(
        "backup",
        lambda host: {"path": "/r1"} if host.name == "r1" else {"paht": "/r2"},
        connection="c",
    ).result()

    assert result["r1"][0].exception is None
    error = result["r2"][0].exception
    assert isinstance(error, OperationInputError)
    assert "on host 'r2'" in str(error)
    assert "unexpected field 'paht' (did you mean 'path'?)" in str(error)
