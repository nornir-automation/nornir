import asyncio
import pathlib
import random
import time
from typing import Any, Awaitable, List

from nornir import InitNornir
from nornir.beta.core.runner import NornirTaskData, Result, TaskRunner, with_retries
from nornir.core import Nornir


@with_retries(attempts=3)
async def i_fail_async(ntd: NornirTaskData, delay: int, attempt: int) -> Result:
    await asyncio.sleep(delay)
    if bool(random.getrandbits(1)):
        raise Exception("I failed")
    msg = f"I succeeded at attempt {attempt}"
    return Result(result=msg, ntd=ntd)


@with_retries(attempts=3)
def i_fail_sync(ntd: NornirTaskData, delay: int, attempt: int) -> Result:
    time.sleep(delay)
    if bool(random.getrandbits(1)):
        raise Exception("I failed")
    msg = f"I succeeded at attempt {attempt}"
    return Result(result=msg, ntd=ntd)


async def hello_async(ntd: NornirTaskData, delay: int) -> Result:
    await asyncio.sleep(delay)
    if bool(random.getrandbits(1)):
        raise Exception("I failed")
    msg = f"{ntd.host} was here"
    return Result(result=msg, ntd=ntd)


def hello_sync(ntd: NornirTaskData, delay: int) -> Result:
    time.sleep(delay)
    if bool(random.getrandbits(1)):
        raise Exception("I failed")
    msg = f"{ntd.host} was here"
    return Result(result=msg, ntd=ntd)


def grouped_task_sync(ntd: NornirTaskData) -> Result:
    sub_results: List[Result] = []
    # Make this a bit more seamless
    r = hello_sync(ntd=ntd, delay=1)
    sub_results.append(r)
    r = hello_sync(ntd=ntd, delay=1)
    sub_results.append(r)
    return Result(ntd=ntd, sub_results=sub_results, result="awesome")


def test_simple_sync(nornir: Nornir) -> None:
    r = TaskRunner(task=hello_sync, nornir=nornir).run(delay=1)
    for host, result in r.items():
        print(f"{host}: {result.exception or result.result}")


def test_simple_async(nornir: Nornir) -> None:
    r = TaskRunner(task=hello_async, nornir=nornir).run(delay=1)
    for host, result in r.items():
        print(f"{host}: {result.exception or result.result}")


def test_simple_sync_with_retries(nornir: Nornir) -> None:
    r = TaskRunner(task=i_fail_sync, nornir=nornir).run(delay=1)
    for host, result in r.items():
        print(f"{host}: {result.exception or result.result}")


def test_simple_async_with_retries(nornir: Nornir) -> None:
    r = TaskRunner(task=i_fail_async, nornir=nornir).run(delay=1)
    for host, result in r.items():
        print(f"{host}: {result.exception or result.result}")


def test_advanced_async(nornir: Nornir) -> None:
    async def done(fs: List[Awaitable[Any]]) -> None:
        for f in asyncio.as_completed(fs):
            result = await f
            print(result)

    loop = asyncio.get_event_loop()
    fs = TaskRunner(task=hello_async, nornir=nornir).prepare_futures(delay=1)
    loop.run_until_complete(done(fs))


def test_grouped_task_sync(nornir: Nornir) -> None:
    r = TaskRunner(task=grouped_task_sync, nornir=nornir).run()
    for host, result in r.items():
        print(f"{host}: {result.exception or result.result}: {result.sub_results}")


if __name__ == "__main__":
    dir_path = pathlib.Path(__file__).parent.joinpath("tests")

    nornir = InitNornir(
        inventory={"options": {"hosts": {f"host{i}": {} for i in range(1, 1000)}}},
        core={"num_workers": 500},
    )
    #  test_simple_sync(nornir)
    #  test_simple_async(nornir)
    #  test_simple_sync_with_retries(nornir)
    #  test_simple_async_with_retries(nornir)
    #  test_advanced_async(nornir)
    test_grouped_task_sync(nornir)
