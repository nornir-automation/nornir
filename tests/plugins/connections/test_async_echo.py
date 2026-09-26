from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.inventory import Defaults, Groups, Host, Hosts, Inventory
from nornir.core.plugins.connections import CapabilityConnectionPluginRegister
from nornir.core.task import Task
from nornir.plugins.runners import AsyncioRunner

from .async_echo import AsyncEcho


class LoopbackEchoServer:
    def __init__(self) -> None:
        self._server: asyncio.AbstractServer | None = None
        self._handlers: set[asyncio.Task[None]] = set()
        self._writers: set[asyncio.StreamWriter] = set()
        self.handler_started = asyncio.Event()
        self.handler_errors: list[BaseException] = []
        self.port = 0

    @property
    def is_serving(self) -> bool:
        return self._server is not None and self._server.is_serving()

    @property
    def handlers(self) -> frozenset[asyncio.Task[None]]:
        return frozenset(self._handlers)

    @property
    def writers(self) -> frozenset[asyncio.StreamWriter]:
        return frozenset(self._writers)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._accept, "127.0.0.1", 0)
        sockets = self._server.sockets
        assert sockets
        address = cast("tuple[str, int]", sockets[0].getsockname())
        self.port = address[1]

    def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        handler = asyncio.create_task(self._handle(reader, writer))
        self._handlers.add(handler)
        handler.add_done_callback(self._record_handler_result)

    def _record_handler_result(self, handler: asyncio.Task[None]) -> None:
        if handler.cancelled():
            self.handler_errors.append(asyncio.CancelledError())
            return
        error = handler.exception()
        if error is not None:
            self.handler_errors.append(error)

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._writers.add(writer)
        self.handler_started.set()
        try:
            while data := await reader.read(64 * 1024):
                writer.write(data)
                await writer.drain()
        except ConnectionError:
            pass
        finally:
            self._writers.discard(writer)
            writer.close()
            with suppress(ConnectionError):
                await writer.wait_closed()

    async def close_and_drain(self) -> None:
        server = self._server
        if server is not None:
            server.close()
            await server.wait_closed()
            self._server = None

        for writer in tuple(self._writers):
            writer.close()
        if self._handlers:
            await asyncio.gather(*self._handlers, return_exceptions=True)


@pytest.fixture
def loopback_echo_server() -> LoopbackEchoServer:
    return LoopbackEchoServer()


@pytest.fixture(autouse=True)
def isolated_capability_registry() -> Iterator[None]:
    available = CapabilityConnectionPluginRegister.available
    previous = available.copy()
    available.clear()
    yield
    available.clear()
    available.update(previous)
    CapabilityConnectionPluginRegister.available = available


async def echo_twice(
    task: Task, payload: bytes
) -> tuple[bytes, bytes, bool, AsyncEcho]:
    first = cast(
        "AsyncEcho",
        await task.host.aget_connection("async-echo", task.nornir.config),
    )
    first_reply = await first.send(payload)
    second = cast(
        "AsyncEcho",
        await task.host.aget_connection("async-echo", task.nornir.config),
    )
    second_reply = await second.send(payload)
    return first_reply, second_reply, first is second, first


def test_async_echo_round_trip_reuse_and_host_cleanup(
    loopback_echo_server: LoopbackEchoServer,
) -> None:
    async def exercise() -> None:
        server = loopback_echo_server
        await server.start()
        CapabilityConnectionPluginRegister.register("async-echo", AsyncEcho)
        hosts = Hosts(
            {
                name: Host(name, hostname="127.0.0.1", port=server.port)
                for name in ("first", "second", "third")
            }
        )
        nr = Nornir(
            inventory=Inventory(hosts=hosts, groups=Groups(), defaults=Defaults()),
            config=Config(),
            runner=AsyncioRunner(),
        )
        plugins: list[AsyncEcho] = []

        try:
            result = await nr.arun(echo_twice, payload=b"nornir async echo")

            assert list(result) == ["first", "second", "third"]
            for host_result in result.values():
                first, second, reused, plugin = cast(
                    "tuple[bytes, bytes, bool, AsyncEcho]", host_result[0].result
                )
                assert first == b"nornir async echo"
                assert second == b"nornir async echo"
                assert reused
                plugins.append(plugin)

            assert len({id(plugin) for plugin in plugins}) == len(hosts)
            for host in hosts.values():
                await host.aclose_connections()
            for plugin in plugins:
                await plugin.aclose()
                await plugin.aclose()
        finally:
            for host in hosts.values():
                await host.aclose_connections()
            await server.close_and_drain()

        assert not server.is_serving
        assert not server.writers
        assert server.handlers
        assert all(handler.done() for handler in server.handlers)
        assert not server.handler_errors

    asyncio.run(exercise())


def test_async_echo_cancelled_partial_open_closes_transport_and_handler(
    loopback_echo_server: LoopbackEchoServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        server = loopback_echo_server
        await server.start()
        plugin = AsyncEcho()
        drain_started = asyncio.Event()
        client_writers: list[asyncio.StreamWriter] = []

        async def block_client_drain(writer: asyncio.StreamWriter) -> None:
            client_writers.append(writer)
            drain_started.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(asyncio.StreamWriter, "drain", block_client_drain)
        opening = asyncio.create_task(
            plugin.aopen("127.0.0.1", None, None, server.port, None)
        )

        try:
            await drain_started.wait()
            await server.handler_started.wait()
            opening.cancel()
            with pytest.raises(asyncio.CancelledError):
                await opening

            with pytest.raises(RuntimeError, match="not open"):
                _ = plugin.connection
            assert len(client_writers) == 1
            assert client_writers[0].is_closing()
            await plugin.aclose()
            await plugin.aclose()
        finally:
            if not opening.done():
                opening.cancel()
                with suppress(asyncio.CancelledError):
                    await opening
            await plugin.aclose()
            await server.close_and_drain()

        assert not server.is_serving
        assert not server.writers
        assert server.handlers
        assert all(handler.done() for handler in server.handlers)
        assert not server.handler_errors

    asyncio.run(exercise())


def test_async_echo_failed_partial_open_closes_transport_and_handler(
    loopback_echo_server: LoopbackEchoServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        server = loopback_echo_server
        await server.start()
        plugin = AsyncEcho()
        client_writers: list[asyncio.StreamWriter] = []

        async def fail_client_drain(writer: asyncio.StreamWriter) -> None:
            client_writers.append(writer)
            await server.handler_started.wait()
            raise ConnectionResetError("injected open failure")

        monkeypatch.setattr(asyncio.StreamWriter, "drain", fail_client_drain)

        try:
            with pytest.raises(ConnectionResetError, match="injected open failure"):
                await plugin.aopen("127.0.0.1", None, None, server.port, None)

            with pytest.raises(RuntimeError, match="not open"):
                _ = plugin.connection
            assert len(client_writers) == 1
            assert client_writers[0].is_closing()
            await plugin.aclose()
            await plugin.aclose()
        finally:
            await plugin.aclose()
            await server.close_and_drain()

        assert not server.is_serving
        assert not server.writers
        assert server.handlers
        assert all(handler.done() for handler in server.handlers)
        assert not server.handler_errors

    asyncio.run(exercise())
