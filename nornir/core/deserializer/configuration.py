import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, Union, List, cast

from nornir.core import configuration
from nornir.core.deserializer.inventory import Inventory

from nornir._vendor.pydantic import BaseSettings, Field

import ruamel.yaml


logger = logging.getLogger(__name__)


class BaseNornirSettings(BaseSettings):
    def _build_values(self, init_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        config_settings = init_kwargs.pop("__config_settings__", {})
        return {**config_settings, **self._build_environ(), **init_kwargs}


class SSHConfig(BaseNornirSettings):
    config_file: str = Field(
        default="~/.ssh/config", description="Path to ssh configuration file"
    )

    class Config:
        env_prefix = "NORNIR_SSH_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs: Any) -> configuration.SSHConfig:
        s = SSHConfig(**kwargs)
        s.config_file = str(Path(s.config_file).expanduser())
        return configuration.SSHConfig(**s.dict())


class InventoryConfig(BaseNornirSettings):
    plugin: str = Field(
        default="nornir.plugins.inventory.simple.SimpleInventory",
        description="Import path to inventory plugin",
    )
    options: Dict[str, Any] = Field(
        default={}, description="kwargs to pass to the inventory plugin"
    )
    transform_function: str = Field(
        default="",
        description=(
            "Path to transform function. The transform_function "
            "you provide will run against each host in the inventory"
        ),
    )
    transform_function_options: Dict[str, Any] = Field(
        default={}, description="kwargs to pass to the transform_function"
    )

    class Config:
        env_prefix = "NORNIR_INVENTORY_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs: Any) -> configuration.InventoryConfig:
        inv = InventoryConfig(**kwargs)
        return configuration.InventoryConfig(
            plugin=cast(Type[Inventory], _resolve_import_from_string(inv.plugin)),
            options=inv.options,
            transform_function=_resolve_import_from_string(inv.transform_function),
            transform_function_options=inv.transform_function_options,
        )


class LoggingConfig(BaseNornirSettings):
    enabled: Optional[bool] = Field(
        default=None, description="Whether to configure logging or not"
    )
    level: str = Field(default="INFO", description="Logging level")
    file: str = Field(default="nornir.log", description="Logging file")
    format: str = Field(
        default="%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s",
        description="Logging format",
    )
    to_console: bool = Field(
        default=False, description="Whether to log to console or not"
    )
    loggers: List[str] = Field(default=["nornir"], description="Loggers to configure")

    class Config:
        env_prefix = "NORNIR_LOGGING_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs) -> configuration.LoggingConfig:
        conf = cls(**kwargs)
        return configuration.LoggingConfig(
            enabled=conf.enabled,
            level=conf.level.upper(),
            file_=conf.file,
            format_=conf.format,
            to_console=conf.to_console,
            loggers=conf.loggers,
        )


class Jinja2Config(BaseNornirSettings):
    filters: str = Field(
        default="", description="Path to callable returning jinja filters to be used"
    )

    class Config:
        env_prefix = "NORNIR_JINJA2_"
        ignore_extra = False

    @classmethod
    def deserialize(cls, **kwargs: Any) -> configuration.Jinja2Config:
        c = Jinja2Config(**kwargs)
        jinja_filter_func = _resolve_import_from_string(c.filters)
        jinja_filters = jinja_filter_func() if jinja_filter_func else {}
        return configuration.Jinja2Config(filters=jinja_filters)


class CoreConfig(BaseNornirSettings):
    num_workers: int = Field(
        default=20,
        description="Number of Nornir worker threads that are run at the same time by default",
    )
    raise_on_error: bool = Field(
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
    def deserialize(cls, **kwargs: Any) -> configuration.CoreConfig:
        c = CoreConfig(**kwargs)
        return configuration.CoreConfig(**c.dict())


class Config(BaseNornirSettings):
    core: CoreConfig = CoreConfig()
    inventory: InventoryConfig = InventoryConfig()
    ssh: SSHConfig = SSHConfig()
    logging: LoggingConfig = LoggingConfig()
    jinja2: Jinja2Config = Jinja2Config()
    user_defined: Dict[str, Any] = Field(
        default={}, description="User-defined <k, v> pairs"
    )

    class Config:
        env_prefix = "NORNIR_"
        ignore_extra = False

    @classmethod
    def deserialize(
        cls, __config_settings__: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> configuration.Config:
        __config_settings__ = __config_settings__ or {}
        c = Config(
            core=CoreConfig(
                __config_settings__=__config_settings__.pop("core", {}),
                **kwargs.pop("core", {}),
            ),
            ssh=SSHConfig(
                __config_settings__=__config_settings__.pop("ssh", {}),
                **kwargs.pop("ssh", {}),
            ),
            inventory=InventoryConfig(
                __config_settings__=__config_settings__.pop("inventory", {}),
                **kwargs.pop("inventory", {}),
            ),
            logging=LoggingConfig(
                __config_settings__=__config_settings__.pop("logging", {}),
                **kwargs.pop("logging", {}),
            ),
            jinja2=Jinja2Config(
                __config_settings__=__config_settings__.pop("jinja2", {}),
                **kwargs.pop("jinja2", {}),
            ),
            __config_settings__=__config_settings__,
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
    def load_from_file(cls, config_file: str, **kwargs: Any) -> configuration.Config:
        config_dict: Dict[str, Any] = {}
        if config_file:
            yml = ruamel.yaml.YAML(typ="safe")
            with open(config_file, "r") as f:
                config_dict = yml.load(f) or {}
        return Config.deserialize(__config_settings__=config_dict, **kwargs)


def _resolve_import_from_string(
    import_path: Union[Callable[..., Any], str]
) -> Optional[Callable[..., Any]]:
    try:
        if not import_path:
            return None
        elif callable(import_path):
            return import_path
        module_name, obj_name = import_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
    except Exception:
        logger.error("Failed to import %r", import_path, exc_info=True)
        raise
