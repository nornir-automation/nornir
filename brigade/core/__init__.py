import logging
import sys
import traceback
from multiprocessing.dummy import Pool

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
        raise_on_error (``bool``): If set to ``True``, :meth:`run` method of will
          raise an exception if at least a host failed.

    Attributes:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        num_workers(``int``): How many hosts run in parallel
        raise_on_error (``bool``): If set to ``True``, :meth:`run` method of will
          raise an exception if at least a host failed.
    """

    def __init__(self, inventory, dry_run, num_workers=20, raise_on_error=True):
        self.inventory = inventory

        self.dry_run = dry_run
        self.num_workers = num_workers
        self.raise_on_error = raise_on_error

        format = "\033[31m%(asctime)s - %(name)s - %(levelname)s"
        format += " - %(funcName)20s() - %(message)s\033[0m"
        logging.basicConfig(
            level=logging.ERROR,
            format=format,
        )

    def filter(self, **kwargs):
        """
        See :py:meth:`brigade.core.inventory.Inventory.filter`

        Returns:
            :obj:`Brigade`: A new object with same configuration as ``self`` but filtered inventory.
        """
        b = Brigade(**self.__dict__)
        b.inventory = self.inventory.filter(**kwargs)
        return b

    def _run_serial(self, task, **kwargs):
        t = Task(task, **kwargs)
        result = AggregatedResult()
        for host in self.inventory.hosts.values():
            try:
                logger.debug("{}: running task {}".format(host.name, t))
                r = t._start(host=host, brigade=self, dry_run=self.dry_run)
                result[host.name] = r
            except Exception as e:
                logger.error("{}: {}".format(host, e))
                result.failed_hosts[host.name] = e
                result.tracebacks[host.name] = traceback.format_exc()
        return result

    def _run_parallel(self, task, num_workers, **kwargs):
        result = AggregatedResult()

        pool = Pool(processes=num_workers)
        result_pool = [pool.apply_async(run_task, args=(h, self, Task(task, **kwargs)))
                       for h in self.inventory.hosts.values()]
        pool.close()
        pool.join()

        for r in result_pool:
            host, res, exc, traceback = r.get()
            if exc:
                result.failed_hosts[host] = exc
                result.tracebacks[host] = exc
            else:
                result[host] = res
        return result

    def run(self, task, num_workers=None, **kwargs):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            num_workers(``int``): Override for how many hosts to run in paralell for this task
            **kwargs: additional argument to pass to ``task`` when calling it

        Raises:
            :obj:`brigade.core.exceptions.BrigadeExceptionError`: if at least a task fails
              and self.raise_on_error is set to ``True``

        Returns:
            :obj:`brigade.core.task.AggregatedResult`: results of each execution
        """
        num_workers = num_workers or self.num_workers

        if num_workers == 1:
            result = self._run_serial(task, **kwargs)
        else:
            result = self._run_parallel(task, num_workers, **kwargs)

        if self.raise_on_error:
            result.raise_on_error()
        return result


def run_task(host, brigade, task):
    try:
        logger.debug("{}: running task {}".format(host.name, task))
        r = task._start(host=host, brigade=brigade, dry_run=brigade.dry_run)
        return host.name, r, None, None
    except Exception as e:
        logger.error("{}: {}".format(host, e))
        return host.name, None, e, traceback.format_exc()
