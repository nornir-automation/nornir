import asyncio
import pathlib
import time
from typing import Any, Awaitable, List

from nornir import InitNornir
from nornir.beta.core.runner import TaskRunner, with_retries
from nornir.core import Nornir
from nornir.core.inventory import Host
from nornir.core.task import Result


@with_retries(attempts=3)
async def i_fail_async(host: Host, delay: int, attempt: int) -> None:
    print(f"this is attempt {attempt} for {host}")
    await asyncio.sleep(delay)
    if attempt < 2:
        raise Exception(1)


@with_retries(attempts=3)
def i_fail_sync(host: Host, delay: int, attempt: int) -> None:
    print(f"this is attempt {attempt} for {host}")
    time.sleep(delay)
    if attempt < 2:
        raise Exception(1)


async def hello_async(host: Host, delay: int) -> Result:
    await asyncio.sleep(delay)
    msg = f"{host} was here"
    print(msg)
    return Result(host=host, result=msg)


def hello_sync(host: Host, delay: int) -> Result:
    time.sleep(delay)
    msg = f"{host} was here"
    print(msg)
    return Result(host=host, result=msg)


def simple_sync(nornir: Nornir) -> None:
    TaskRunner(task=hello_sync, nornir=nornir).run(delay=1)


def simple_async(nornir: Nornir) -> None:
    TaskRunner(task=hello_async, nornir=nornir).run(delay=1)


def simple_sync_with_retries(nornir: Nornir) -> None:
    TaskRunner(task=i_fail_sync, nornir=nornir).run(delay=1)


def simple_async_with_retries(nornir: Nornir) -> None:
    TaskRunner(task=i_fail_async, nornir=nornir).run(delay=1)


def advanced_async(nornir: Nornir) -> None:
    async def done(fs: List[Awaitable[Any]]) -> None:
        for f in asyncio.as_completed(fs):
            result = await f
            print(result)

    loop = asyncio.get_event_loop()
    fs = TaskRunner(task=hello_async, nornir=nornir).prepare_futures(delay=1)
    loop.run_until_complete(done(fs))


if __name__ == "__main__":
    dir_path = pathlib.Path(__file__).parent.joinpath("tests")

    nornir = InitNornir(
        inventory={"options": {"hosts": {f"host{i}": {} for i in range(1, 1000)}}},
        core={"num_workers": 500},
    )
    #  simple_sync(nornir)
    #  simple_async(nornir)
    #  simple_sync_with_retries(nornir)
    #  simple_async_with_retries(nornir)
    advanced_async(nornir)
