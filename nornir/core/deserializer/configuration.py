from typing import Any, Callable, Dict, List, Optional

import importlib
import logging

from nornir.core import configuration

from pydantic import BaseSettings

import ruamel.yaml


logger = logging.getLogger("nornir")


class SSHConfig(BaseSettings):
    """
    Args:
        config_file: User ssh_config_file
    """

    config_file: str = "~/.ssh/config"

    class Config:
        env_prefix = "NORNIR_SSH_"
        ignore_extra = False

    @classmethod
    def deserialize(self, **kwargs) -> configuration.SSHConfig:
        s = SSHConfig(**kwargs)
        return configuration.SSHConfig(config_file=s.config_file)


class InventoryConfig(BaseSettings):
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

    class Config:
        env_prefix = "NORNIR_INVENTORY_"
        ignore_extra = False

    @classmethod
    def deserialize(self, **kwargs) -> configuration.InventoryConfig:
        inv = InventoryConfig(**kwargs)
        return configuration.InventoryConfig(
            plugin=_resolve_import_from_string(inv.plugin),
            options=inv.options,
            transform_function=_resolve_import_from_string(inv.transform_function),
        )


class LoggingConfig(BaseSettings):
    level: str = "debug"
    file: str = "nornir.log"
    format: str = "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s"
    to_console: bool = False
    loggers: List[str] = ["nornir"]

    class Config:
        env_prefix = "NORNIR_LOGGING_"
        ignore_extra = False

    @classmethod
    def deserialize(self, **kwargs) -> configuration.LoggingConfig:
        logging_config = LoggingConfig(**kwargs)
        return configuration.LoggingConfig(
            level=getattr(logging, logging_config.level.upper()),
            file_=logging_config.file,
            format_=logging_config.format,
            to_console=logging_config.to_console,
            loggers=logging_config.loggers,
        )


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

    inventory: InventoryConfig = InventoryConfig()
    ssh: SSHConfig = SSHConfig()
    logging: LoggingConfig = LoggingConfig()
    jinja_filters: str = ""
    num_workers: int = 20
    raise_on_error: bool = False
    user_defined: Dict[str, Any] = {}

    class Config:
        env_prefix = "NORNIR_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.Config:
        c = Config(
            ssh=SSHConfig(**kwargs.pop("ssh", {})),
            inventory=InventoryConfig(**kwargs.pop("inventory", {})),
            logging=LoggingConfig(**kwargs.pop("logging", {})),
            **kwargs,
        )

        jinja_filter_func = _resolve_import_from_string(c.jinja_filters)
        jinja_filters = jinja_filter_func() if jinja_filter_func else {}
        return configuration.Config(
            inventory=InventoryConfig.deserialize(**c.inventory.dict()),
            ssh=SSHConfig.deserialize(**c.ssh.dict()),
            logging=LoggingConfig.deserialize(**c.logging.dict()),
            jinja_filters=jinja_filters,
            num_workers=c.num_workers,
            raise_on_error=c.raise_on_error,
            user_defined=c.user_defined,
        )

    @classmethod
    def load_from_file(cls, config_file: str, **kwargs) -> configuration.Config:
        config_dict = {}
        if config_file:
            yml = ruamel.yaml.YAML(typ="safe")
            with open(config_file, "r") as f:
                config_dict = yml.load(f) or {}
        return Config.deserialize(**{**config_dict, **kwargs})


def _resolve_import_from_string(import_path: Any) -> Optional[Callable[..., Any]]:
    try:
        if not import_path:
            return None
        elif callable(import_path):
            return import_path
        module_name = ".".join(import_path.split(".")[:-1])
        obj_name = import_path.split(".")[-1]
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
    except Exception as e:
        logger.error(f"failed to load import_path '{import_path}'\n{e}")
        raise
