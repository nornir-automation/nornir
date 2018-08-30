import importlib
import logging
import logging.config
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseSettings

import ruamel.yaml


class SSHConfig(BaseSettings):
    """
    Args:
        config_file: User ssh_config_file
    """

    config_file: str = "~/.ssh/config"

    class Config:
        env_prefix = "NORNIR_SSH_"


class Inventory(BaseSettings):
    """
    Args:
        plugin: Path to inventory modules.
        transform_function: Path to transform function. The transform_function you provide
            will run against each host in the inventory
        options: Arguments to pass to the inventory plugin
    """

    plugin: Any = "nornir.plugins.inventory.simple.SimpleInventory"
    options: Dict[str, Any] = {}
    transform_function: Any = ""

    def get_plugin(self) -> Optional[Callable[..., Any]]:
        return _resolve_import_from_string(self.plugin)

    def get_transform_function(self) -> Optional[Callable[..., Any]]:
        return _resolve_import_from_string(self.transform_function)

    class Config:
        env_prefix = "NORNIR_INVENTORY_"


class Logging(BaseSettings):
    level: str = "debug"
    file: str = "nornir.log"
    format: str = "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s"
    to_console: bool = False
    loggers: List[str] = ["nornir"]

    class Config:
        env_prefix = "NORNIR_LOGGING_"

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
            loggers[logger] = {"level": self.level.upper(), "handlers": handlers_list}

        if rootHandlers:
            logging.config.dictConfig(dictConfig)


class Config(BaseSettings):
    """
    Args:
        inventory: Dictionary with Inventory options
        jinja_filters: Path to callable returning jinja filters to be used
        raise_on_error: If set to ``True``, (:obj:`nornir.core.Nornir.run`) method of
            will raise an exception if at least a host failed
        num_workers: Number of Nornir worker processes that are run at the same time
            configuration can be overridden on individual tasks by using the


    """

    inventory: Inventory = Inventory()
    jinja_filters: str = ""
    num_workers: int = 20
    raise_on_error: bool = False
    ssh: SSHConfig = SSHConfig()
    user_defined: Dict[str, Any] = {}
    logging: Logging = Logging()

    class Config:
        env_prefix = "NORNIR_"

    def __init__(self, path: str = "", **kwargs) -> None:
        if path:
            with open(path, "r") as f:
                yml = ruamel.yaml.YAML(typ="safe")
                data = yml.load(f) or {}
            data.update(kwargs)
        else:
            data = kwargs
        data["ssh"] = SSHConfig(**data.pop("ssh", {}))
        data["inventory"] = Inventory(**data.pop("inventory", {}))
        data["logging"] = Logging(**data.pop("logging", {}))
        super().__init__(**data)


def _resolve_import_from_string(import_path: Any) -> Optional[Callable[..., Any]]:
    if not import_path:
        return None
    elif callable(import_path):
        return import_path
    module_name = ".".join(import_path.split(".")[:-1])
    obj_name = import_path.split(".")[-1]
    module = importlib.import_module(module_name)
    return getattr(module, obj_name)
