from __future__ import annotations

from typing import Any, Literal, Protocol

from nornir.core.configuration import Config
from nornir.core.plugins.register import PluginRegister

CONNECTIONS_PLUGIN_PATH = "nornir.plugins.connections"
CAPABILITY_CONNECTIONS_PLUGIN_PATH = "nornir.plugins.capability_connections"

ConnectionCapability = Literal["sync", "asyncio"]


class ConnectionPlugin(Protocol):
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
        """Connect to the device.

        Populates the attribute :attr:`connection` with the underlying connection.
        """

    def close(self) -> None:
        """Close the connection with the device."""

    @property
    def connection(self) -> Any:
        """Established connection."""


class CapabilityConnectionPlugin(Protocol):
    """Common contract for plugins in the capability-aware registry.

    Plugins are constructible without arguments and without device I/O. Capability
    reporting is synchronous, performs no device I/O, and is stable for the lifetime
    of the instance. Operations are required only for the capabilities declared.
    """

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        """Return exactly ``{'sync'}``, ``{'asyncio'}``, or both capabilities."""
        ...

    @property
    def connection(self) -> Any:
        """The established transport after a successful open."""


class SyncCapabilityConnectionPlugin(ConnectionPlugin, CapabilityConnectionPlugin, Protocol):
    """Capability-aware plugin with synchronous open and close operations."""


class AsyncCapabilityConnectionPlugin(CapabilityConnectionPlugin, Protocol):
    """Capability-aware plugin with native asynchronous operations.

    Both operations are native coroutine methods and must not block the event loop.
    An unsuccessful or cancelled open releases acquired resources, and close is
    idempotent, including after an unsuccessful opening attempt.
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

    async def aclose(self) -> None:
        """Close the transport; safe to call more than once."""


class DualCapabilityConnectionPlugin(
    SyncCapabilityConnectionPlugin, AsyncCapabilityConnectionPlugin, Protocol
):
    """Plugin whose sync and async modes reuse the same established transport."""


ConnectionPluginRegister: PluginRegister[type[ConnectionPlugin]] = PluginRegister(
    CONNECTIONS_PLUGIN_PATH
)

CapabilityConnectionPluginRegister: PluginRegister[type[CapabilityConnectionPlugin]] = (
    PluginRegister(CAPABILITY_CONNECTIONS_PLUGIN_PATH)
)
CapabilityConnectionPluginRegister.available = {}
