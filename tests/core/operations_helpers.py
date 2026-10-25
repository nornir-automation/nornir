"""Shared Operations, models, tasks and inventory for the tests of feature 004."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nornir.core import Nornir
from nornir.core.configuration import Config, CoreConfig
from nornir.core.inventory import Host, Hosts, Inventory
from nornir.core.operations import Operation, OperationRegistry
from nornir.core.processor import Processors

if TYPE_CHECKING:
    from collections.abc import Iterable

    from nornir.core.plugins.runners import RunnerPlugin
    from nornir.core.processor import Processor
    from nornir.core.task import Task


@dataclass
class GetConfigInput:
    retrieve: str = "running"
    sanitized: bool = False


@dataclass
class GetConfigOutput:
    config: str


class GetConfig(Operation[GetConfigInput, GetConfigOutput]):
    name = "get_config"


@dataclass
class BackupInput:
    path: str


@dataclass
class BackupOutput:
    written: str


class Backup(Operation[BackupInput, BackupOutput]):
    name = "backup"


def ios_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    return GetConfigOutput(config=f"ios {params.retrieve} {task.host.name}")


def eos_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    return GetConfigOutput(config=f"eos {params.retrieve} {task.host.name}")


def junos_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    return GetConfigOutput(config=f"junos {params.retrieve} {task.host.name}")


async def aios_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    await asyncio.sleep(0)
    return GetConfigOutput(config=f"ios {params.retrieve} {task.host.name}")


async def aeos_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    await asyncio.sleep(0)
    return GetConfigOutput(config=f"eos {params.retrieve} {task.host.name}")


def backup_task(task: Task, params: BackupInput) -> BackupOutput:
    return BackupOutput(written=params.path)


PLATFORMS = {"r1": "ios", "r2": "eos", "r3": "junos"}


def make_nornir(
    runner: RunnerPlugin,
    platforms: dict[str, str | None] | None = None,
    operation_connection: str | None = None,
    processors: Iterable[Processor] = (),
) -> Nornir:
    """Build a Nornir object with one host per entry of ``platforms``.

    Returns:
        The Nornir object.

    """
    platforms = dict(PLATFORMS) if platforms is None else platforms
    hosts = Hosts(
        {name: Host(name=name, platform=platform) for name, platform in platforms.items()}
    )
    return Nornir(
        inventory=Inventory(hosts=hosts),
        runner=runner,
        config=Config(core=CoreConfig(operation_connection=operation_connection)),
        processors=Processors(list(processors)),
    )


def register_get_config(connection: str = "napalm") -> None:
    """Register the synchronous ``get_config`` tasks for ios, eos and junos."""
    for platform, task in (
        ("ios", ios_get_config),
        ("eos", eos_get_config),
        ("junos", junos_get_config),
    ):
        OperationRegistry.register(
            operation="get_config", platform=platform, connection=connection, task=task
        )
