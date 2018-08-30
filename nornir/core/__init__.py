import logging
import logging.handlers
import sys
from multiprocessing.dummy import Pool

from nornir.core.configuration import Config
from nornir.core.task import AggregatedResult, Task
from nornir.plugins.connections import register_default_connection_plugins

register_default_connection_plugins()
logger = logging.getLogger(__name__)


class Data(object):
    """
    This class is just a placeholder to share data amongst different
    versions of Nornir after running ``filter`` multiple times.

    Attributes:
        failed_hosts (list): Hosts that have failed to run a task properly
    """

    def __init__(self):
        self.failed_hosts = set()

    def recover_host(self, host):
        """Remove ``host`` from list of failed hosts."""
        self.failed_hosts.discard(host)

    def reset_failed_hosts(self):
        """Reset failed hosts and make all hosts available for future tasks."""
        self.failed_hosts = set()

    def to_dict(self):
        """ Return a dictionary representing the object. """
        return self.__dict__


class Nornir(object):
    """
    This is the main object to work with. It contains the inventory and it serves
    as task dispatcher.

    Arguments:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(:obj:`nornir.core.Data`): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration object
        config_file (``str``): Path to Yaml configuration file

    Attributes:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(:obj:`nornir.core.Data`): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration parameters
    """

    def __init__(self, inventory, dry_run, config=None, config_file=None, data=None):

        self.data = data or Data()
        self.inventory = inventory
        self.inventory.nornir = self
        self.data.dry_run = dry_run

        if config_file:
            self.config = Config(config_file=config_file)
        else:
            self.config = config or Config()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connections(on_good=True, on_failed=True)

    @property
    def dry_run(self):
        return self.data.dry_run

    def filter(self, *args, **kwargs):
        """
        See :py:meth:`nornir.core.inventory.Inventory.filter`

        Returns:
            :obj:`Nornir`: A new object with same configuration as ``self`` but filtered inventory.
        """
        b = Nornir(dry_run=self.dry_run, **self.__dict__)
        b.inventory = self.inventory.filter(*args, **kwargs)
        return b

    def _run_serial(self, task, hosts, **kwargs):
        result = AggregatedResult(kwargs.get("name") or task.__name__)
        for host in hosts:
            result[host.name] = Task(task, **kwargs).start(host, self)
        return result

    def _run_parallel(self, task, hosts, num_workers, **kwargs):
        result = AggregatedResult(kwargs.get("name") or task.__name__)

        pool = Pool(processes=num_workers)
        result_pool = [
            pool.apply_async(Task(task, **kwargs).start, args=(h, self)) for h in hosts
        ]
        pool.close()
        pool.join()

        for rp in result_pool:
            r = rp.get()
            result[r.host.name] = r
        return result

    def run(
        self,
        task,
        num_workers=None,
        raise_on_error=None,
        on_good=True,
        on_failed=False,
        **kwargs,
    ):
        """
        Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            num_workers(``int``): Override for how many hosts to run in paralell for this task
            raise_on_error (``bool``): Override raise_on_error behavior
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            **kwargs: additional argument to pass to ``task`` when calling it

        Raises:
            :obj:`nornir.core.exceptions.NornirExecutionError`: if at least a task fails
              and self.config.raise_on_error is set to ``True``

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: results of each execution
        """
        num_workers = num_workers or self.config.num_workers

        run_on = []
        if on_good:
            for name, host in self.inventory.hosts.items():
                if name not in self.data.failed_hosts:
                    run_on.append(host)
        if on_failed:
            for name, host in self.inventory.hosts.items():
                if name in self.data.failed_hosts:
                    run_on.append(host)

        task_name = kwargs.get("name") or task.__name__
        if num_workers == 1:
            workers_str = "1 worker"
        else:
            workers_str = f"{num_workers} workers"
        logger.info(
            "Running task '%s' with %s on %d hosts",
            task_name,
            workers_str,
            len(self.inventory),
        )

        if num_workers == 1:
            result = self._run_serial(task, run_on, **kwargs)
        else:
            result = self._run_parallel(task, run_on, num_workers, **kwargs)

        raise_on_error = (
            raise_on_error if raise_on_error is not None else self.config.raise_on_error
        )  # noqa
        if raise_on_error:
            result.raise_on_error()
        else:
            self.data.failed_hosts.update(result.failed_hosts.keys())
        return result

    def to_dict(self):
        """ Return a dictionary representing the object. """
        return {"data": self.data.to_dict(), "inventory": self.inventory.to_dict()}

    def close_connections(self, on_good=True, on_failed=False):
        def close_connections_task(task):
            task.host.close_connections()

        self.run(task=close_connections_task, on_good=on_good, on_failed=on_failed)


def configure_logging(config: Config) -> None:
    if not config.logging_enabled:
        return
    nornir_logger = logging.getLogger("nornir")
    # configure logging only if the user didn't touch nornir logger using
    # dictConfig or via a programmatic way
    if nornir_logger.level == logging.NOTSET and not nornir_logger.handlers:
        nornir_logger.propagate = False
        nornir_logger.setLevel(config.logging_level)
        formatter = logging.Formatter(config.logging_format)
        if config.logging_file:
            handler = logging.handlers.RotatingFileHandler(
                config.logging_file, maxBytes=1024 * 1024 * 10, backupCount=20
            )
            handler.setFormatter(formatter)
            nornir_logger.addHandler(handler)
        if config.logging_to_console:
            # log INFO and DEBUG to stdout
            h1 = logging.StreamHandler(sys.stdout)
            h1.setFormatter(formatter)
            h1.setLevel(logging.DEBUG)
            h1.addFilter(lambda record: record.levelno <= logging.INFO)
            nornir_logger.addHandler(h1)

            # log WARNING, ERROR and CRITICAL to stderr
            h2 = logging.StreamHandler(sys.stderr)
            h2.setFormatter(formatter)
            h2.setLevel(logging.WARNING)
            nornir_logger.addHandler(h2)


def InitNornir(config_file="", dry_run=False, **kwargs):
    """
    Arguments:
        config_file(str): Path to the configuration file (optional)
        dry_run(bool): Whether to simulate changes or not
        **kwargs: Extra information to pass to the
            :obj:`nornir.core.configuration.Config` object

    Returns:
        :obj:`nornir.core.Nornir`: fully instantiated and configured
    """
    conf = Config(config_file=config_file, **kwargs)

    configure_logging(conf)
    inv_class = conf.inventory
    inv_args = getattr(conf, inv_class.__name__, {})
    transform_function = conf.transform_function
    inv = inv_class(transform_function=transform_function, **inv_args)

    return Nornir(inventory=inv, dry_run=dry_run, config=conf)
