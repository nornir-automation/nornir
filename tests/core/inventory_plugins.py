"""Inventory plugins and transform functions shared by the async inventory tests."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any

from nornir.core.inventory import Defaults, Groups, Host, Hosts, Inventory
from nornir.core.plugins.inventory import InventoryCapability

HOST_NAMES = ("h1", "h2", "h3")


@dataclass
class Recorder:
    """Records which plugin and transform members ran, and on which thread."""

    events: list[tuple[str, ...]] = field(default_factory=list)
    threads: dict[str, int] = field(default_factory=dict)

    def record(self, *event: str) -> None:
        self.events.append(event)
        self.threads[event[0]] = threading.get_ident()

    def names(self) -> list[str]:
        return [event[0] for event in self.events]

    def reset(self) -> None:
        self.events.clear()
        self.threads.clear()


RECORDER = Recorder()


def build_test_inventory() -> Inventory:
    hosts = Hosts({name: Host(name=name, hostname=f"{name}.example.com") for name in HOST_NAMES})
    return Inventory(hosts=hosts, groups=Groups(), defaults=Defaults())


class LegacyPlugin:
    def __init__(self, **kwargs: Any) -> None:
        RECORDER.record("init")

    def load(self) -> Inventory:
        RECORDER.record("load")
        return build_test_inventory()


class SyncCapabilityPlugin(LegacyPlugin):
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        RECORDER.record("get_capabilities")
        return frozenset({"sync"})


class AsyncCapabilityPlugin:
    def __init__(self, **kwargs: Any) -> None:
        RECORDER.record("init")

    def get_capabilities(self) -> frozenset[InventoryCapability]:
        RECORDER.record("get_capabilities")
        return frozenset({"asyncio"})

    async def aload(self) -> Inventory:
        RECORDER.record("aload")
        await asyncio.sleep(0)
        return build_test_inventory()


class DualCapabilityPlugin(SyncCapabilityPlugin, AsyncCapabilityPlugin):
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        RECORDER.record("get_capabilities")
        return frozenset({"sync", "asyncio"})


class BlockingLegacyPlugin:
    """Legacy plugin whose ``load`` sets ``started`` and waits until the test sets ``event``."""

    def __init__(
        self,
        event: threading.Event,
        started: threading.Event | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.event = event
        self.started = started or threading.Event()
        self.timeout = timeout

    def load(self) -> Inventory:
        RECORDER.record("load")
        self.started.set()
        if not self.event.wait(self.timeout):
            msg = "load() was never released"
            raise TimeoutError(msg)
        return build_test_inventory()


def sync_transform(host: Host, **kwargs: Any) -> None:
    RECORDER.record("transform", host.name)
    host.data.update(kwargs)


async def async_transform(host: Host, **kwargs: Any) -> None:
    RECORDER.record("start", host.name)
    await asyncio.sleep(0)
    host.data.update(kwargs)
    RECORDER.record("end", host.name)
