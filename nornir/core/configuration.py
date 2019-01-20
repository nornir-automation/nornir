import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING, Type


if TYPE_CHECKING:
    from nornir.core.deserializer.inventory import Inventory  # noqa


class SSHConfig(object):
    __slots__ = "config_file"

    def __init__(self, config_file: str) -> None:
        self.config_file = config_file


class InventoryConfig(object):
    __slots__ = "plugin", "options", "transform_function", "transform_function_options"

    def __init__(
        self,
        plugin: Type["Inventory"],
        options: Dict[str, Any],
        transform_function: Optional[Callable[..., Any]],
        transform_function_options: Optional[Dict[str, Any]],
    ) -> None:
        self.plugin = plugin
        self.options = options
        self.transform_function = transform_function
        self.transform_function_options = transform_function_options


class LoggingConfig(object):
    __slots__ = "enabled", "level", "file_path", "format", "to_console"

    def __init__(
        self, enabled: bool, level: str, file_path: str, format: str, to_console: bool
    ) -> None:
        self.enabled = enabled
        self.level = level
        self.file_path = file_path
        self.format = format
        self.to_console = to_console

    def configure(self) -> None:
        nornir_logger = logging.getLogger("nornir")
        root_logger = logging.getLogger()
        # don't configure logging when:
        # 1) enabled equals to False
        # 2) nornir logger's level is something different than NOTSET
        # 3) if root logger has some handlers (which means you know how to
        #    configure logging already)
        # 4) if root logger's level is something different than WARNING
        #    (which is default)
        if (
            not self.enabled
            or nornir_logger.level != logging.NOTSET
            or root_logger.hasHandlers()
            or root_logger.level != logging.WARNING
        ):
            return

        nornir_logger.propagate = False
        nornir_logger.setLevel(self.level)
        formatter = logging.Formatter(self.format)
        if self.file_path:
            handler = logging.handlers.RotatingFileHandler(
                str(Path(self.file_path)), maxBytes=1024 * 1024 * 10, backupCount=20
            )
            handler.setFormatter(formatter)
            nornir_logger.addHandler(handler)

        if self.to_console:
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


class Jinja2Config(object):
    __slots__ = "filters"

    def __init__(self, filters: Optional[Dict[str, Callable[..., Any]]]) -> None:
        self.filters = filters or {}


class CoreConfig(object):
    __slots__ = ("num_workers", "raise_on_error")

    def __init__(self, num_workers: int, raise_on_error: bool) -> None:
        self.num_workers = num_workers
        self.raise_on_error = raise_on_error


class Config(object):
    __slots__ = ("core", "ssh", "inventory", "jinja2", "logging", "user_defined")

    def __init__(
        self,
        inventory: InventoryConfig,
        ssh: SSHConfig,
        logging: LoggingConfig,
        jinja2: Jinja2Config,
        core: CoreConfig,
        user_defined: Dict[str, Any],
    ) -> None:
        self.inventory = inventory
        self.ssh = ssh
        self.logging = logging
        self.jinja2 = jinja2
        self.core = core
        self.user_defined = user_defined
