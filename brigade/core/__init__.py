import logging
import sys
import traceback
from multiprocessing.dummy import Pool

from brigade.core.configuration import Config
from brigade.core.task import AggregatedResult, Task
from brigade.plugins.tasks import connections


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
        config (:obj:`brigade.core.configuration.Config`): Configuration object
        config_file (``str``): Path to Yaml configuration file
        available_connections (``dict``): dict of connection types that will be made available.
            Defaults to :obj:`brigade.plugins.tasks.connections.available_connections`

    Attributes:
        inventory (:obj:`brigade.core.inventory.Inventory`): Inventory to work with
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`brigade.core.configuration.Config`): Configuration parameters
        available_connections (``dict``): dict of connection types are available
    """

    def __init__(self, inventory, dry_run, config=None, config_file=None,
                 available_connections=None):
        self.inventory = inventory
        self.inventory.brigade = self

        self.dry_run = dry_run
        if config_file:
            self.config = Config(config_file=config_file)
        else:
            self.config = config or Config()

        format = "\033[31m%(asctime)s - %(name)s - %(levelname)s"
        format += " - %(funcName)20s() - %(message)s\033[0m"
        logging.basicConfig(
            level=logging.ERROR,
            format=format,
        )
        if available_connections is not None:
            self.available_connections = available_connections
        else:
            self.available_connections = connections.available_connections

    def filter(self, **kwargs):
        """
        See :py:meth:`brigade.core.inventory.Inventory.filter`

        Returns:
            :obj:`Brigade`: A new object with same configuration as ``self`` but filtered inventory.
        """
        b = Brigade(**self.__dict__)
        b.inventory = self.inventory.filter(**kwargs)
        return b

    def _run_serial(self, task, dry_run, **kwargs):
        t = Task(task, **kwargs)
        result = AggregatedResult()
        for host in self.inventory.hosts.values():
            try:
                logger.debug("{}: running task {}".format(host.name, t))
                r = t._start(host=host, brigade=self, dry_run=dry_run)
                result[host.name] = r
            except Exception as e:
                logger.error("{}: {}".format(host, e))
                result.failed_hosts[host.name] = e
                result.tracebacks[host.name] = traceback.format_exc()
        return result

    def _run_parallel(self, task, num_workers, dry_run, **kwargs):
        result = AggregatedResult()

        pool = Pool(processes=num_workers)
        result_pool = [pool.apply_async(run_task, args=(h, self, dry_run, Task(task, **kwargs)))
                       for h in self.inventory.hosts.values()]
        pool.close()
        pool.join()

        for r in result_pool:
            host, res, exc, traceback = r.get()
            if exc:
                result.failed_hosts[host] = exc
                result.tracebacks[host] = traceback
            else:
                result[host] = res
        return result

    def run(self, task, num_workers=None, dry_run=None, **kwargs):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            num_workers(``int``): Override for how many hosts to run in paralell for this task
            dry_run(``bool``): Whether if we are testing the changes or not
            **kwargs: additional argument to pass to ``task`` when calling it

        Raises:
            :obj:`brigade.core.exceptions.BrigadeExecutionError`: if at least a task fails
              and self.config.raise_on_error is set to ``True``

        Returns:
            :obj:`brigade.core.task.AggregatedResult`: results of each execution
        """
        num_workers = num_workers or self.config.num_workers

        if num_workers == 1:
            result = self._run_serial(task, dry_run, **kwargs)
        else:
            result = self._run_parallel(task, num_workers, dry_run, **kwargs)

        if self.config.raise_on_error:
            result.raise_on_error()
        return result


def run_task(host, brigade, dry_run, task):
    try:
        logger.debug("{}: running task {}".format(host.name, task))
        r = task._start(host=host, brigade=brigade, dry_run=dry_run)
        return host.name, r, None, None
    except Exception as e:
        logger.error("{}: {}".format(host, e))
        return host.name, None, e, traceback.format_exc()
