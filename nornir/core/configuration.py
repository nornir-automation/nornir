import logging
import logging.config
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Type


if TYPE_CHECKING:
    from nornir.core.deserializer.inventory import Inventory  # noqa


class SSHConfig(object):
    __slots__ = "config_file"

    def __init__(self, config_file: str) -> None:
        self.config_file = config_file


class InventoryConfig(object):
    __slots__ = "plugin", "options", "transform_function"

    def __init__(
        self,
        plugin: Type["Inventory"],
        options: Dict[str, Any],
        transform_function: Optional[Callable[..., Any]],
    ) -> None:
        self.plugin = plugin
        self.options = options
        self.transform_function = transform_function


class LoggingConfig(object):
    __slots__ = "level", "file", "format", "to_console", "loggers"

    def __init__(
        self, level: int, file_: str, format_: str, to_console: bool, loggers: List[str]
    ) -> None:
        self.level = level
        self.file = file_
        self.format = format_
        self.to_console = to_console
        self.loggers = loggers

    def configure(self):
        rootHandlers: List[Any] = []
        root = {
            "level": "CRITICAL" if self.loggers else self.level.upper(),
            "handlers": rootHandlers,
            "formatter": "simple",
        }
        handlers: Dict[str, Any] = {}
        loggers: Dict[str, Any] = {}
        dictConfig = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"simple": {"format": self.format}},
            "handlers": handlers,
            "loggers": loggers,
            "root": root,
        }
        handlers_list = []
        if self.file:
            root["handlers"].append("info_file_handler")
            handlers_list.append("info_file_handler")
            handlers["info_file_handler"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "NOTSET",
                "formatter": "simple",
                "filename": self.file,
                "maxBytes": 10485760,
                "backupCount": 20,
                "encoding": "utf8",
            }
        if self.to_console:
            root["handlers"].append("info_console")
            handlers_list.append("info_console")
            handlers["info_console"] = {
                "class": "logging.StreamHandler",
                "level": "NOTSET",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }

        for logger in self.loggers:
            loggers[logger] = {"level": self.level, "handlers": handlers_list}

        if rootHandlers:
            logging.config.dictConfig(dictConfig)


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
