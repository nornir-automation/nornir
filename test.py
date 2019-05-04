import asyncio
import pathlib
import time

from nornir import InitNornir
from nornir.beta.core.runner import TaskRunner, with_retries
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


if __name__ == "__main__":
    dir_path = pathlib.Path(__file__).parent.joinpath("tests")

    nornir = InitNornir(
        inventory={"options": {"hosts": {f"host{i}": {} for i in range(1, 1000)}}},
        core={"num_workers": 1000},
    )

    TaskRunner(task=hello_async, nornir=nornir).run(delay=1)
    #  TaskRunner(task=hello_sync, nornir=nornir).run(delay=1)
    #  TaskRunner(task=i_fail_async, nornir=nornir).run(delay=1)
    #  TaskRunner(task=i_fail_sync, nornir=nornir).run(delay=1)
