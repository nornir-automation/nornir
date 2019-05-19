import asyncio
import logging
from dataclasses import asdict, dataclass, field
from multiprocessing.dummy import Pool
from typing import Any, Awaitable, Callable, Dict, List, Optional

from nornir.core import Nornir
from nornir.core.inventory import Host


@dataclass
class NornirTaskData:
    host: Host
    nornir: Nornir
    name: str


@dataclass
class Result(object):
    ntd: NornirTaskData
    result: Any = None
    sub_results: List["Result"] = field(default_factory=list)
    changed: bool = False
    diff: str = ""
    exception: Optional[BaseException] = None
    severity_level: int = logging.INFO

    def __repr__(self) -> str:
        return f'{self.__class__.__name__} "{self.ntd.name}": {asdict(self)}'

    def __str__(self) -> str:
        if self.exception:
            return str(self.exception)

        else:
            return str(self.result)


@dataclass
class AggregatedResults(Dict[str, Result]):
    name: str = ""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} ({self.name}): {super().__repr__()}"


def _result_wrapper(result: Any, ntd: NornirTaskData) -> Result:
    if isinstance(result, Result):
        result.ntd = ntd
        return result
    else:
        return Result(result=result, ntd=ntd)


def _func_wrapper(
    func: Callable[..., Result], ntd: NornirTaskData, *args: Any, **kwargs: Any
) -> Any:
    try:
        return _result_wrapper(func(ntd=ntd, *args, **kwargs), ntd)
    except Exception as e:
        return Result(ntd=ntd, exception=e)


async def _async_func_wrapper(
    func: Callable[..., Awaitable[Result]],
    ntd: NornirTaskData,
    *args: Any,
    **kwargs: Any,
) -> Any:
    try:
        result = await func(ntd, *args, **kwargs)
        return _result_wrapper(result, ntd)
    except Exception as e:
        return Result(ntd=ntd, exception=e)


class TaskRunner:
    def __init__(
        self,
        task: Callable[..., Any],
        nornir: Nornir,
        name: str = None,
        severity_level: int = logging.INFO,
        on_good: bool = True,
        on_failed: bool = False,
    ) -> None:
        self.task = task
        self.name = name or task.__class__.__qualname__
        self.nornir = nornir
        self.num_workers = nornir.config.core.num_workers
        self.severity_level = severity_level

        self.hosts: List[Host] = []
        if on_good:
            for name, host in nornir.inventory.hosts.items():
                if name not in nornir.data.failed_hosts:
                    self.hosts.append(host)
        if on_failed:
            for name, host in nornir.inventory.hosts.items():
                if name in nornir.data.failed_hosts:
                    self.hosts.append(host)

    def run(self, **kwargs: Any) -> AggregatedResults:
        if asyncio.iscoroutinefunction(self.task):
            result = self._run_async(**kwargs)
        else:
            result = self._run_sync(**kwargs)
        agg_results = AggregatedResults(name=self.name)
        for r in result:
            agg_results[r.ntd.host.name] = r
        return agg_results

    def _run_async(self, **kwargs: Any) -> List[Result]:
        loop = asyncio.get_event_loop()
        hosts = [
            _async_func_wrapper(
                self.task,
                NornirTaskData(host=h, nornir=self.nornir, name=self.name),
                **kwargs,
            )
            for h in self.hosts
        ]
        return loop.run_until_complete(asyncio.gather(*hosts))

    def _run_sync(self, **kwargs: Any) -> List[Result]:
        pool = Pool(processes=self.num_workers)
        result_pool = [
            pool.apply_async(
                _func_wrapper,
                args=(
                    self.task,
                    NornirTaskData(host=h, nornir=self.nornir, name=self.name),
                ),
                kwds=kwargs,
            )
            for h in self.hosts
        ]
        pool.close()
        pool.join()
        return [r.get() for r in result_pool]

    def prepare_futures(self, **kwargs: Any) -> List[Awaitable[Result]]:
        # TODO: fix return types
        fs: List[Awaitable[Any]] = []
        for h in self.hosts:
            f = asyncio.ensure_future(
                self.task(
                    NornirTaskData(host=h, nornir=self.nornir, name=self.name), **kwargs
                )
            )
            fs.append(f)
        return fs


class with_retries:
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts

    def __call__(self, func: Callable[..., Any]) -> Any:
        if asyncio.iscoroutinefunction(func):
            return self.async_wrapper(func)
        else:
            return self.sync_wrapper(func)

    def async_wrapper(self, func: Callable[..., Any]) -> Any:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(0, self.attempts):
                try:
                    return await func(*args, **kwargs, attempt=i)
                except Exception:
                    if i + 1 == self.attempts:
                        raise

        return wrapper

    def sync_wrapper(self, func: Callable[..., Any]) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for i in range(0, self.attempts):
                try:
                    return func(*args, **kwargs, attempt=i)
                except Exception:
                    if i + 1 == self.attempts:
                        raise

        return wrapper
