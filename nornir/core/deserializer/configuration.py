import importlib
import logging
from deepmerge import Merger
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast

from nornir.core import configuration
from nornir.core.deserializer.inventory import Inventory

from pydantic import BaseSettings, Schema

import ruamel.yaml


logger = logging.getLogger(__name__)


def deep_merge_settings(
    base: Dict[str, Any], *overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """ Merges each of the overrides in turn into the base object"""
    my_merger = Merger([(dict, ["merge"])], ["override"], ["override"])
    result = base
    for override in overrides:
        if override:
            my_merger.merge(result, override)
    return result


class NornirBaseSettings(BaseSettings):
    def _build_values(self, init_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """ Merges config file, environment variables and passed parameters
            in a configurable way

            If __deep_merge__=True:
                Implements deep merging for the config file data, environment vars and
                passed parameters while maintaing the precedence order.

            If __deep_merge__=False (default):
                Preserves the nornir 2.0 behaviour. If any parameters are passed, these
                are used without considering config file or env vars. If not provided,
                then the resulting merge of config file and environment variables is
                taken instead.
        """
        deep_merge = init_kwargs.pop("__deep_merge__", False)
        config_settings = init_kwargs.pop("__config_settings__", {})
        if deep_merge:
            values = {**config_settings}  # force copy so as not to modify original
            return deep_merge_settings(values, self._build_environ(), init_kwargs)
        else:
            return {**config_settings, **self._build_environ(), **init_kwargs}


class SSHConfig(NornirBaseSettings):
    config_file: str = Schema(
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


class InventoryConfig(NornirBaseSettings):
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
    transform_function_options: Dict[str, Any] = Schema(
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


class LoggingConfig(NornirBaseSettings):
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
    def deserialize(cls, **kwargs: Any) -> configuration.LoggingConfig:
        logging_config = LoggingConfig(**kwargs)
        return configuration.LoggingConfig(
            level=getattr(logging, logging_config.level.upper()),
            file_=logging_config.file,
            format_=logging_config.format,
            to_console=logging_config.to_console,
            loggers=logging_config.loggers,
        )


class Jinja2Config(NornirBaseSettings):
    filters: str = Schema(
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


class CoreConfig(NornirBaseSettings):
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
    def deserialize(cls, **kwargs: Any) -> configuration.CoreConfig:
        c = CoreConfig(**kwargs)
        return configuration.CoreConfig(**c.dict())


class Config(NornirBaseSettings):
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
    def deserialize(
        cls,
        config_settings: Optional[Dict[str, Any]] = None,
        deep_merge: bool = False,
        **kwargs: Any,
    ) -> configuration.Config:
        if config_settings is None:
            config_settings = {}
        # Handle merging user_defined here, since there isn't a Pydantic model
        # handle this automatically as there are for the other config sections
        if deep_merge:
            user_defined = deep_merge_settings(
                config_settings.pop("user_defined", {}), kwargs.pop("user_defined", {})
            )
        else:
            user_defined = kwargs.pop("user_defined", {}) or config_settings.pop(
                "user_defined", {}
            )
        c = Config(
            __deep_merge__=deep_merge,
            core=CoreConfig(
                __config_settings__=config_settings.get("core", {}),
                __deep_merge__=deep_merge,
                **kwargs.pop("core", {}),
            ),
            ssh=SSHConfig(
                __config_settings__=config_settings.get("ssh", {}),
                __deep_merge__=deep_merge,
                **kwargs.pop("ssh", {}),
            ),
            inventory=InventoryConfig(
                __config_settings__=config_settings.get("inventory", {}),
                __deep_merge__=deep_merge,
                **kwargs.pop("inventory", {}),
            ),
            logging=LoggingConfig(
                __config_settings__=config_settings.get("logging", {}),
                __deep_merge__=deep_merge,
                **kwargs.pop("logging", {}),
            ),
            jinja2=Jinja2Config(
                __config_settings__=config_settings.get("jinja2", {}),
                __deep_merge__=deep_merge,
                **kwargs.pop("jinja2", {}),
            ),
            user_defined=user_defined,
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
    def load_from_file(
        cls, config_file: str, deep_merge: bool = False, **kwargs: Any
    ) -> configuration.Config:
        config_dict: Dict[str, Any] = {}
        if config_file:
            yml = ruamel.yaml.YAML(typ="safe")
            with open(config_file, "r") as f:
                config_dict = yml.load(f) or {}
        return Config.deserialize(
            config_settings=config_dict, deep_merge=deep_merge, **kwargs
        )


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
        return cast(Callable[..., Any], getattr(module, obj_name))
    except Exception as e:
        logger.error(f"failed to load import_path '{import_path}'\n{e}")
        raise
