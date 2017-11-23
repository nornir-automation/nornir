import concurrent.futures
import logging
import sys

from brigade.core.exceptions import BrigadeExecutionError
from brigade.core.task import AggregatedResult, Task


if sys.version_info.major == 2:
    import copy_reg
    import types

    # multithreading requires objects passed around to be pickable
    # following methods allow py2 to know how to pickle methods
    def _pickle_method(method):
        func_name = method.im_func.__name__
        obj = method.im_self
        cls = method.im_class
        return _unpickle_method, (func_name, obj, cls)

    def _unpickle_method(func_name, obj, cls):
        for cls in cls.mro():
            try:
                func = cls.__dict__[func_name]
            except KeyError:
                pass
            else:
                break
        return func.__get__(obj, cls)

    copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)


logger = logging.getLogger("brigade")


class Brigade(object):
    """
    This is the main object to work with. It contains the inventory and it serves
    as task dispatcher.

    Arguments:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        num_workers(``int``): How many hosts run in parallel

    Attributes:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        num_workers(``int``): How many hosts run in parallel
    """

    def __init__(self, inventory, dry_run, num_workers=5):
        """
        Args:
            inventory(brigade.core.inventory.Inventory): An Inventory object.
            dry_run(bool): Whether this is a dry run or not.
        """
        self.inventory = inventory
        self.dry_run = dry_run
        self.num_workers = num_workers

        logging.basicConfig(
            level=logging.ERROR,
            format='\033[31m%(asctime)s - %(name)s - %(levelname)s - %(message)s\033[0m',
        )

    def filter(self, **kwargs):
        """
        See :py:meth:`brigade.core.inventory.Inventory.filter`

        Returns:
            :obj:`Brigade`: A new object with same configuration as ``self`` but filtered inventory.
        """
        return Brigade(inventory=self.inventory.filter(**kwargs),
                       dry_run=self.dry_run, num_workers=self.num_workers)

    def _run_single_thread(self, task, **kwargs):
        exception = False
        result = AggregatedResult()
        for host in self.inventory.hosts.values():
            try:
                r = task._start(host=host, brigade=self, dry_run=self.dry_run)
            except Exception as e:
                exception = True
                r = e
            result[host.name] = r
        if exception:
            logger.error(result)
            raise BrigadeExecutionError(result)
        return result

    def _run_multithread(self, task, **kwargs):
        exception = False
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            tasks = {executor.submit(task._start,
                                     host=host, brigade=self, dry_run=self.dry_run): host
                     for host in self.inventory.hosts.values()}
            result = AggregatedResult()
            for t in concurrent.futures.as_completed(tasks):
                host = tasks[t]
                try:
                    r = t.result()
                except Exception as e:
                    exception = True
                    r = e
                result[host.name] = r
        if exception:
            logger.error(result)
            raise BrigadeExecutionError(result)
        return result

    def run(self, task, **kwargs):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            dict: dict where keys are hostnames and values are each individual result

        Raises:
            :obj:`brigade.core.exceptions.BrigadeExecutionError`: If any task raises an
              Exception
        """
        t = Task(task, **kwargs)
        if self.num_workers == 1:
            return self._run_single_thread(t, **kwargs)
        else:
            return self._run_multithread(t, **kwargs)
