from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nornir.core.configuration import Config
    from nornir.core.plugins.connections import ConnectionCapability


class AsyncEcho:
    """Async-only byte echo connection used by integration tests and documentation."""

    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._send_lock = asyncio.Lock()

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})

    @property
    def connection(self) -> AsyncEcho:
        if self._reader is None or self._writer is None or self._writer.is_closing():
            raise RuntimeError("AsyncEcho is not open")
        return self

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
        if hostname is None or port is None:
            raise ValueError("AsyncEcho requires hostname and port")
        if self._writer is not None and not self._writer.is_closing():
            raise RuntimeError("AsyncEcho is already open")

        writer: asyncio.StreamWriter | None = None
        try:
            reader, writer = await asyncio.open_connection(hostname, port)
            self._reader = reader
            self._writer = writer
            await writer.drain()
        except BaseException:
            self._reader = None
            if self._writer is writer:
                self._writer = None
            if writer is not None:
                writer.close()
                with suppress(ConnectionError):
                    await writer.wait_closed()
            raise

    async def send(self, payload: bytes) -> bytes:
        async with self._send_lock:
            reader = self._reader
            writer = self._writer
            if reader is None or writer is None or writer.is_closing():
                raise RuntimeError("AsyncEcho is not open")
            writer.write(payload)
            await writer.drain()
            return await reader.readexactly(len(payload))

    async def aclose(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None
        if writer is None:
            return
        writer.close()
        with suppress(ConnectionError):
            await writer.wait_closed()
