"""Proposed public signatures; design artifact, not installed implementation.

Connection protocols belong in nornir.core.plugins.connections. The existing
ConnectionPlugin and ConnectionPluginRegister retain their signatures and types.
Plugins satisfy these protocols structurally, without inheritance or unsupported
operation stubs. The runner contracts belong in their existing runner modules.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from nornir.core.configuration import Config
from nornir.core.inventory import Host
from nornir.core.plugins.connections import ConnectionPlugin
from nornir.core.plugins.register import PluginRegister
from nornir.core.task import AggregatedResult, Task

ConnectionCapability = Literal["sync", "asyncio"]


class CapabilityConnectionPlugin(Protocol):
    """Common contract for all plugins in the capability-aware registry.

    Classes must be constructible without arguments. Capability reporting is
    synchronous, performs no device I/O, and is stable for the instance's lifetime.
    Operations are required only for declared capabilities. Connection is accessed
    after a successful open, not probed during pre-open validation.
    """

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        """Return exactly {'sync'}, {'asyncio'}, or {'sync', 'asyncio'}."""
        ...

    @property
    def connection(self) -> Any:
        """The established transport."""
        ...


class SyncCapabilityConnectionPlugin(ConnectionPlugin, CapabilityConnectionPlugin, Protocol):
    """Capability-aware plugin with synchronous open and close operations."""


class AsyncCapabilityConnectionPlugin(CapabilityConnectionPlugin, Protocol):
    """Capability-aware plugin with native async operations.

    Both operations must be async def methods and must not block the event loop.
    An unsuccessful or cancelled aopen releases resources it acquired before it
    exits. aclose is idempotent, including after an unsuccessful opening attempt.
    """

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
        """Establish the connection using the legacy open parameter contract."""
        ...

    async def aclose(self) -> None:
        """Close the transport; safe to call more than once."""
        ...


class DualCapabilityConnectionPlugin(
    SyncCapabilityConnectionPlugin, AsyncCapabilityConnectionPlugin, Protocol
):
    """Both paths operate on the same connection, regardless of opening mode."""


CAPABILITY_CONNECTIONS_PLUGIN_PATH = "nornir.plugins.capability_connections"

# New registry only: allocate instance-owned storage because PluginRegister's
# initial available dictionary is otherwise shared between registry instances.
CapabilityConnectionPluginRegister: PluginRegister[type[CapabilityConnectionPlugin]] = (
    PluginRegister(CAPABILITY_CONNECTIONS_PLUGIN_PATH)
)
CapabilityConnectionPluginRegister.available = {}


class AsyncRunnerPlugin(Protocol):
    """Optional sibling runner protocol; existing RunnerPlugin is unchanged."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the runner."""
        ...

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run on the caller's loop; cancel and await owned work before propagating cancellation."""
        ...


class AsyncioRunner:
    """Reference runner signatures; registered under asyncio.

    num_workers must be a positive integer; booleans are not worker counts.
    """

    def __init__(self, num_workers: int = 20) -> None:
        """Reject non-integers with TypeError and nonpositive counts with ValueError."""
        raise NotImplementedError

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Raise RunnerNotSyncError pointing to await nr.arun(...)."""
        raise NotImplementedError

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Fan out task copies with bounded concurrency; preserve host result order."""
        raise NotImplementedError
