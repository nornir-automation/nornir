"""Public contracts added by the asyncio runner feature.

This file is a design artifact, not shipped code: it fixes the signatures that the
implementation must expose. Both protocols are optional siblings of the existing
``ConnectionPlugin`` and ``RunnerPlugin``, which are not modified. Plugins satisfy them
structurally, and the core detects support by the presence of ``aopen`` / ``arun`` as
coroutine functions (see research R2 and R8).
"""

from __future__ import annotations

from typing import Any, Protocol

from nornir.core.configuration import Config
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, Task


class AsyncConnectionPlugin(Protocol):
    """Optional async counterpart of :class:`nornir.core.plugins.connections.ConnectionPlugin`.

    A plugin may implement this contract, the synchronous one, or both. Registration is
    unchanged: the existing ``nornir.plugins.connections`` entry-point group.

    Rules for the async members:

    1. ``aopen`` and ``aclose`` must not block the event loop; wrap blocking libraries with
       ``asyncio.to_thread``.
    2. ``aclose`` must be safe to call more than once.
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
        """Connect to the device; same parameters, same order as ``open``.

        Populates :attr:`connection` with the underlying connection.
        """

    async def aclose(self) -> None:
        """Close the connection with the device. Idempotent."""

    @property
    def connection(self) -> Any:
        """Established connection."""


class AsyncRunnerPlugin(Protocol):
    """Optional async counterpart of :class:`nornir.core.plugins.runners.RunnerPlugin`.

    ``Nornir.arun`` dispatches to ``arun`` when the assigned runner has one. A runner that
    has *only* an async path still defines ``run`` so it satisfies ``RunnerPlugin`` for the
    registry and the ``Nornir`` constructor, and raises ``RunnerNotSyncError`` from it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure the plugin."""
        raise NotImplementedError("needs to be implemented by the plugin")

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the given task over all the hosts on the current event loop.

        Must call ``task.copy().astart(host)`` for each host, bound the number in flight,
        key the result by ``host.name`` in the order given, and on cancellation cancel
        and await every in-flight host before letting the cancellation propagate.
        """
        raise NotImplementedError("needs to be implemented by the plugin")


class AsyncioRunner:
    """Reference implementation registered as ``asyncio`` (signature only)."""

    def __init__(self, num_workers: int = 20) -> None: ...

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Raise ``RunnerNotSyncError`` pointing to ``await nr.arun(...)``, unconditionally."""

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        """Run the task over the hosts, at most ``num_workers`` in flight, on the current loop."""
