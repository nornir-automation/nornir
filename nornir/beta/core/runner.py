import asyncio
import logging
from multiprocessing.dummy import Pool
from typing import Any, Awaitable, Callable, List

from nornir.core import Nornir
from nornir.core.inventory import Host


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

    def run(self, **kwargs: Any) -> None:
        if asyncio.iscoroutinefunction(self.task):
            self._run_async(**kwargs)
        else:
            self._run_sync(**kwargs)

    def _run_async(self, **kwargs: Any) -> None:
        loop = asyncio.get_event_loop()
        hosts = [self.task(host, **kwargs) for host in self.hosts]
        loop.run_until_complete(asyncio.gather(*hosts))
        loop.close()

    def _run_sync(self, **kwargs: Any) -> None:
        result = {}

        pool = Pool(processes=self.num_workers)
        result_pool = [
            pool.apply_async(self.task, args=(h,), kwds=kwargs) for h in self.hosts
        ]
        pool.close()
        pool.join()

        for rp in result_pool:
            r = rp.get()
            result[r.host.name] = r

    def prepare_futures(self, **kwargs: Any) -> List[Awaitable[Any]]:
        # TODO: fix return types
        fs: List[Awaitable[Any]] = []
        for host in self.hosts:
            f = asyncio.ensure_future(self.task(host, **kwargs))
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
