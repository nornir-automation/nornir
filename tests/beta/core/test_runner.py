import asyncio
import concurrent
import time
from typing import Any, Awaitable, List, Sequence, cast

from nornir.beta.core.runner import (
    FutureException,
    NornirTaskData,
    Result,
    TaskRunner,
    with_retries,
)
from nornir.core import Nornir


@with_retries(attempts=3)
async def i_fail_async(ntd: NornirTaskData, delay: int, attempt: int) -> Result:
    await asyncio.sleep(delay)
    if ntd.host.name == "dev3.group_2":
        raise Exception("I failed")
    if ntd.host.name == "dev4.group_2" and attempt < 2:
        raise Exception("I failed")
    msg = f"I succeeded at attempt {attempt}"
    return Result(data=msg, ntd=ntd)


@with_retries(attempts=3)
def i_fail_sync(ntd: NornirTaskData, delay: int, attempt: int) -> Result:
    time.sleep(delay)
    if ntd.host.name == "dev3.group_2":
        raise Exception("I failed")
    if ntd.host.name == "dev4.group_2" and attempt < 2:
        raise Exception("I failed")
    msg = f"I succeeded at attempt {attempt}"
    return Result(data=msg, ntd=ntd)


async def task_async(ntd: NornirTaskData, delay: float) -> Result:
    await asyncio.sleep(delay)
    if ntd.host.name == "dev3.group_2":
        raise Exception("I failed")
    return Result(data="I was here", ntd=ntd)


def task_sync(ntd: NornirTaskData, delay: float) -> Result:
    time.sleep(delay)
    if ntd.host.name == "dev3.group_2":
        raise Exception("I failed")
    return Result(data="I was here", ntd=ntd)


def grouped_task_sync(ntd: NornirTaskData) -> Result:
    sub_results: List[Result] = []
    # Make this a bit more seamless
    r = task_sync(ntd=ntd, delay=0.1)
    sub_results.append(r)
    r = task_sync(ntd=ntd, delay=0.1)
    sub_results.append(r)
    return Result(ntd=ntd, sub_results=sub_results, data="awesome")


class Tests:
    def test_simple_sync(self, nornir: Nornir) -> None:
        r = TaskRunner(task=task_sync, nornir=nornir).run(delay=0.1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result.exception
            else:
                assert not result.exception
                assert result.data == "I was here"

    def test_simple_async(self, nornir: Nornir) -> None:
        r = TaskRunner(task=task_async, nornir=nornir).run(delay=0.1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result.exception
            else:
                assert not result.exception
                assert result.data == "I was here"

    def test_simple_sync_with_retries(self, nornir: Nornir) -> None:
        r = TaskRunner(task=i_fail_sync, nornir=nornir).run(delay=0.1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result.exception
            elif host == "dev4.group_2":
                assert not result.exception
                assert result.data == "I succeeded at attempt 2"
            else:
                assert not result.exception
                assert result.data == "I succeeded at attempt 1"

    def test_simple_async_with_retries(self, nornir: Nornir) -> None:
        r = TaskRunner(task=i_fail_async, nornir=nornir).run(delay=0.1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result.exception
            elif host == "dev4.group_2":
                assert not result.exception
                assert result.data == "I succeeded at attempt 2"
            else:
                assert not result.exception
                assert result.data == "I succeeded at attempt 1"

    def test_grouped_task_sync(self, nornir: Nornir) -> None:
        r = TaskRunner(task=grouped_task_sync, nornir=nornir).run()
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result.exception
            else:
                assert len(result.sub_results) == 2
                assert result.data == "awesome"

    def test_async_with_futures(self, nornir: Nornir) -> None:
        async def done(fs: Sequence[Awaitable[Any]]) -> None:
            failed = False
            for f in cast(Sequence[Awaitable[Result]], asyncio.as_completed(fs)):
                try:
                    result = await f
                except FutureException as e:
                    failed = True
                    assert e.exc.args[0] == "I failed"
                    assert e.ntd.host.name == "dev3.group_2"
                assert not result.exception
                assert result.data == "I was here"
            assert failed

        loop = asyncio.get_event_loop()
        fs = TaskRunner(task=task_async, nornir=nornir).async_with_futures(delay=0.1)
        loop.run_until_complete(done(fs))

    def test_sync_with_futures(self, nornir: Nornir) -> None:
        start_time = time.time()
        fs1 = TaskRunner(task=task_sync, nornir=nornir).sync_with_futures(delay=0.1)
        fs2 = TaskRunner(task=task_sync, nornir=nornir).sync_with_futures(delay=0.1)
        for f in concurrent.futures.as_completed({*fs1, *fs2}):
            result = f.result()
            if result.ntd.host.name == "dev3.group_2":
                assert result.exception
            else:
                assert not result.exception
                assert result.data == "I was here"
        end_time = time.time()
        assert end_time - start_time < 0.11, end_time - start_time
