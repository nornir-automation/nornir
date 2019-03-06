import logging
import logging.handlers
import sys
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING, Type, List

from nornir.core.exceptions import ConflictingConfigurationWarning

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
    __slots__ = "enabled", "level", "file", "format", "to_console", "loggers"

    def __init__(
        self,
        enabled: Optional[bool],
        level: str,
        file_: str,
        format_: str,
        to_console: bool,
        loggers: List[str],
    ) -> None:
        self.enabled = enabled
        self.level = level
        self.file = file_
        self.format = format_
        self.to_console = to_console
        self.loggers = loggers

    def configure(self) -> None:
        if not self.enabled:
            return

        root_logger = logging.getLogger()
        if root_logger.hasHandlers() or root_logger.level != logging.WARNING:
            msg = (
                "Native Python logging configuration has been detected, but Nornir "
                "logging is enabled too. "
                "This can lead to unexpected logging results. "
                "Please set logging.enabled config to False "
                "to disable automatic Nornir logging configuration. Refer to "
                "https://nornir.readthedocs.io/en/stable/configuration/index.html#logging"  # noqa
            )
            warnings.warn(msg, ConflictingConfigurationWarning)

        formatter = logging.Formatter(self.format)
        # log INFO and DEBUG to stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
        # log WARNING, ERROR and CRITICAL to stderr
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.setLevel(logging.WARNING)

        for logger_name in self.loggers:
            logger_ = logging.getLogger(logger_name)
            logger_.propagate = False
            logger_.setLevel(self.level)
            if logger_.hasHandlers():
                # Don't add handlers if some handlers are already attached to the logger
                # This is crucial to avoid duplicate handlers
                # Alternative would be to clear all handlers and reconfigure them
                # with Nornir
                # There are several situations this branch can be executed:
                # multiple calls to InitNornir,
                # logging.config.dictConfig configuring 'nornir' logger, etc.
                # The warning is not emitted in this scenario
                continue
            if self.file:
                handler = logging.handlers.RotatingFileHandler(
                    str(Path(self.file)), maxBytes=1024 * 1024 * 10, backupCount=20
                )
                handler.setFormatter(formatter)
                logger_.addHandler(handler)

            if self.to_console:
                logger_.addHandler(stdout_handler)
                logger_.addHandler(stderr_handler)


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
