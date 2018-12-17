import importlib
import logging
from typing import Any, Callable, Dict, List, Optional, Type, cast

from nornir.core import configuration
from nornir.core.deserializer.inventory import Inventory

from pydantic import BaseSettings, Schema

import ruamel.yaml


logger = logging.getLogger(__name__)


class SSHConfig(BaseSettings):
    config_file: str = Schema(
        default="~/.ssh/config", description="Path to ssh configuration file"
    )

    class Config:
        env_prefix = "NORNIR_SSH_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.SSHConfig:
        s = SSHConfig(**kwargs)
        return configuration.SSHConfig(**s.dict())


class InventoryConfig(BaseSettings):
    plugin: str = Schema(
        default="nornir.plugins.inventory.simple.SimpleInventory",
        description="Import path to inventory plugin",
    )
    options: Dict[str, Any] = Schema(
        default={}, description="kwargs to pass to the inventory plugin"
    )
    transform_function: str = Schema(
        default="",
        description=(
            "Path to transform function. The transform_function "
            "you provide will run against each host in the inventory"
        ),
    )

    class Config:
        env_prefix = "NORNIR_INVENTORY_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.InventoryConfig:
        inv = InventoryConfig(**kwargs)
        return configuration.InventoryConfig(
            plugin=cast(Type[Inventory], _resolve_import_from_string(inv.plugin)),
            options=inv.options,
            transform_function=_resolve_import_from_string(inv.transform_function),
        )


class LoggingConfig(BaseSettings):
    level: str = Schema(default="debug", description="Logging level")
    file: str = Schema(default="nornir.log", descritpion="Logging file")
    format: str = Schema(
        default="%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s",
        description="Logging format",
    )
    to_console: bool = Schema(
        default=False, description="Whether to log to console or not"
    )
    loggers: List[str] = Schema(default=["nornir"], description="Loggers to configure")

    class Config:
        env_prefix = "NORNIR_LOGGING_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.LoggingConfig:
        logging_config = LoggingConfig(**kwargs)
        return configuration.LoggingConfig(
            level=getattr(logging, logging_config.level.upper()),
            file_=logging_config.file,
            format_=logging_config.format,
            to_console=logging_config.to_console,
            loggers=logging_config.loggers,
        )


class Jinja2Config(BaseSettings):
    filters: str = Schema(
        default="", description="Path to callable returning jinja filters to be used"
    )

    class Config:
        env_prefix = "NORNIR_JINJA2_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.Jinja2Config:
        c = Jinja2Config(**kwargs)
        jinja_filter_func = _resolve_import_from_string(c.filters)
        jinja_filters = jinja_filter_func() if jinja_filter_func else {}
        return configuration.Jinja2Config(filters=jinja_filters)


class CoreConfig(BaseSettings):
    num_workers: int = Schema(
        default=20,
        description="Number of Nornir worker threads that are run at the same time by default",
    )
    raise_on_error: bool = Schema(
        default=False,
        description=(
            "If set to ``True``, (:obj:`nornir.core.Nornir.run`) method of "
            "will raise exception :obj:`nornir.core.exceptions.NornirExecutionError` "
            "if at least a host failed"
        ),
    )

    class Config:
        env_prefix = "NORNIR_CORE_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.CoreConfig:
        c = CoreConfig(**kwargs)
        return configuration.CoreConfig(**c.dict())


class Config(BaseSettings):
    core: CoreConfig = CoreConfig()
    inventory: InventoryConfig = InventoryConfig()
    ssh: SSHConfig = SSHConfig()
    logging: LoggingConfig = LoggingConfig()
    jinja2: Jinja2Config = Jinja2Config()
    user_defined: Dict[str, Any] = Schema(
        default={}, description="User-defined <k, v> pairs"
    )

    class Config:
        env_prefix = "NORNIR_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.Config:
        c = Config(
            core=CoreConfig(**kwargs.pop("core", {})),
            ssh=SSHConfig(**kwargs.pop("ssh", {})),
            inventory=InventoryConfig(**kwargs.pop("inventory", {})),
            logging=LoggingConfig(**kwargs.pop("logging", {})),
            jinja2=Jinja2Config(**kwargs.pop("jinja2", {})),
            **kwargs,
        )
        return configuration.Config(
            core=CoreConfig.deserialize(**c.core.dict()),
            inventory=InventoryConfig.deserialize(**c.inventory.dict()),
            ssh=SSHConfig.deserialize(**c.ssh.dict()),
            logging=LoggingConfig.deserialize(**c.logging.dict()),
            jinja2=Jinja2Config.deserialize(**c.jinja2.dict()),
            user_defined=c.user_defined,
        )

    @classmethod
    def load_from_file(cls, config_file: str, **kwargs) -> configuration.Config:
        config_dict: Dict[str, Any] = {}
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
        module_name, obj_name = import_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
    except Exception as e:
        logger.error(f"failed to load import_path '{import_path}'\n{e}")
        raise
