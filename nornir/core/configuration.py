import ast
import logging
import logging.handlers
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Type, TYPE_CHECKING, List, TypeVar

from nornir.core.exceptions import ConflictingConfigurationWarning

import ruamel.yaml

if TYPE_CHECKING:
    from nornir.core.deserializer.inventory import Inventory  # noqa


DEFAULT_SSH_CONFIG = str(Path("~/.ssh/config").expanduser())

T = TypeVar("T")


class Parameter:
    def __init__(
        self,
        envvar: str,
        typ: Optional[Type[T]] = None,
        help: str = "",
        default: Optional[T] = None,
    ) -> None:
        if typ is not None:
            self.type: Type[T] = typ
        elif default is not None:
            self.type = default.__class__
        else:
            raise TypeError("either typ or default needs to be specified")
        self.envvar = envvar
        self.help = help
        self.default = default or self.type()

    def resolve(self, value: Optional[T]) -> T:
        v: Optional[Any] = value
        if value is None:
            t = os.environ.get(self.envvar)
            if self.type is bool and t:
                v = t in ["true", "True", "1", "yes"]
            elif self.type is str and t:
                v = t
            elif t:
                v = ast.literal_eval(t) if t is not None else None

        if v is None:
            v = self.default
        return v


class SSHConfig(object):
    __slots__ = ("config_file",)

    class Parameters:
        config_file = Parameter(
            default=DEFAULT_SSH_CONFIG, envvar="NORNIR_SSH_CONFIG_FILE"
        )

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.config_file = self.Parameters.config_file.resolve(config_file)

    def dict(self) -> Dict[str, Any]:
        return {"config_file": self.config_file}


class InventoryConfig(object):
    __slots__ = "plugin", "options", "transform_function", "transform_function_options"

    class Parameters:
        plugin = Parameter(
            typ=str, default="SimpleInventory", envvar="NORNIR_INVENTORY_PLUGIN"
        )
        options = Parameter(default={}, envvar="NORNIR_INVENTORY_OPTIONS")
        transform_function = Parameter(
            typ=str, envvar="NORNIR_INVENTORY_TRANSFORM_FUNCTION"
        )
        transform_function_options = Parameter(
            default={}, envvar="NORNIR_INVENTORY_TRANSFORM_FUNCTION_OPTIONS"
        )

    def __init__(
        self,
        plugin: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        transform_function: Optional[str] = None,
        transform_function_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.plugin = self.Parameters.plugin.resolve(plugin)
        self.options = self.Parameters.options.resolve(options) or {}
        self.transform_function = self.Parameters.transform_function.resolve(
            transform_function
        )
        self.transform_function_options = (
            self.Parameters.transform_function_options.resolve(
                transform_function_options
            )
        )

    def dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "options": self.options,
            "transform_function": self.transform_function,
            "transform_function_options": self.transform_function_options,
        }


class LoggingConfig(object):
    __slots__ = "enabled", "level", "log_file", "format", "to_console", "loggers"

    class Parameters:
        enabled = Parameter(default=True, envvar="NORNIR_LOGGING_ENABLED")
        level = Parameter(default="INFO", envvar="NORNIR_LOGGING_LEVEL")
        log_file = Parameter(default="nornir.log", envvar="NORNIR_LOGGING_LOG_FILE")
        format = Parameter(
            default="%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s",
            envvar="NORNIR_LOGGING_FORMAT",
        )
        to_console = Parameter(default=False, envvar="NORNIR_LOGGING_TO_CONSOLE")
        loggers = Parameter(default=["nornir"], envvar="NORNIR_LOGGING_LOGGERS")

    def __init__(
        self,
        enabled: Optional[bool] = None,
        level: Optional[str] = None,
        log_file: Optional[str] = None,
        format: Optional[str] = None,
        to_console: Optional[bool] = None,
        loggers: Optional[List[str]] = None,
    ) -> None:
        self.enabled = self.Parameters.enabled.resolve(enabled)
        self.level = self.Parameters.level.resolve(level)
        self.log_file = self.Parameters.log_file.resolve(log_file)
        self.format = self.Parameters.format.resolve(format)
        self.to_console = self.Parameters.to_console.resolve(to_console)
        self.loggers = self.Parameters.loggers.resolve(loggers)

    def dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "level": self.level,
            "log_file": self.log_file,
            "format": self.format,
            "to_console": self.to_console,
            "loggers": self.loggers,
        }

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
            if self.log_file:
                handler = logging.handlers.RotatingFileHandler(
                    str(Path(self.log_file)), maxBytes=1024 * 1024 * 10, backupCount=20
                )
                handler.setFormatter(formatter)
                logger_.addHandler(handler)

            if self.to_console:
                logger_.addHandler(stdout_handler)
                logger_.addHandler(stderr_handler)


class RunnerConfig(object):
    __slots__ = ("plugin", "options")

    class Parameters:
        plugin = Parameter(default="threaded", envvar="NORNIR_RUNNER_PLUGIN")
        options = Parameter(default={}, envvar="NORNIR_RUNNER_OPTIONS")

    def __init__(
        self, plugin: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ) -> None:
        self.plugin = self.Parameters.plugin.resolve(plugin)
        self.options = self.Parameters.options.resolve(options)

    def dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "options": self.options,
        }


class CoreConfig(object):
    __slots__ = "raise_on_error"

    class Parameters:
        raise_on_error = Parameter(default=False, envvar="NORNIR_CORE_RAISE_ON_ERROR")

    def __init__(self, raise_on_error: Optional[bool] = None) -> None:
        self.raise_on_error = self.Parameters.raise_on_error.resolve(raise_on_error)

    def dict(self) -> Dict[str, Any]:
        return {
            "raise_on_error": self.raise_on_error,
        }


class Config(object):
    __slots__ = (
        "core",
        "runner",
        "ssh",
        "inventory",
        "logging",
        "user_defined",
    )

    def __init__(
        self,
        inventory: Optional[InventoryConfig] = None,
        ssh: Optional[SSHConfig] = None,
        logging: Optional[LoggingConfig] = None,
        core: Optional[CoreConfig] = None,
        runner: Optional[RunnerConfig] = None,
        user_defined: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.inventory = inventory or InventoryConfig()
        self.ssh = ssh or SSHConfig()
        self.logging = logging or LoggingConfig()
        self.core = core or CoreConfig()
        self.runner = runner or RunnerConfig()
        self.user_defined = user_defined or {}

    @classmethod
    def from_dict(
        cls,
        inventory: Dict[str, Any] = None,
        ssh: Optional[Dict[str, Any]] = None,
        logging: Optional[Dict[str, Any]] = None,
        core: Optional[Dict[str, Any]] = None,
        runner: Optional[Dict[str, Any]] = None,
        user_defined: Optional[Dict[str, Any]] = None,
    ) -> "Config":
        return cls(
            inventory=InventoryConfig(**inventory or {}),
            ssh=SSHConfig(**ssh or {}),
            logging=LoggingConfig(**logging or {}),
            core=CoreConfig(**core or {}),
            runner=RunnerConfig(**runner or {}),
            user_defined=user_defined or {},
        )

    @classmethod
    def from_file(
        cls,
        config_file: str,
        inventory: Optional[Dict[str, Any]] = None,
        ssh: Optional[Dict[str, Any]] = None,
        logging: Optional[Dict[str, Any]] = None,
        core: Optional[Dict[str, Any]] = None,
        runner: Optional[Dict[str, Any]] = None,
        user_defined: Optional[Dict[str, Any]] = None,
    ) -> "Config":
        inventory = inventory or {}
        ssh = ssh or {}
        logging = logging or {}
        core = core or {}
        runner = runner or {}
        user_defined = user_defined or {}
        with open(config_file, "r") as f:
            yml = ruamel.yaml.YAML(typ="safe")
            data = yml.load(f)
        return cls(
            inventory=InventoryConfig(**{**data.get("inventory", {}), **inventory}),
            ssh=SSHConfig(**{**data.get("ssh", {}), **ssh}),
            logging=LoggingConfig(**{**data.get("logging", {}), **logging}),
            core=CoreConfig(**{**data.get("core", {}), **core}),
            runner=RunnerConfig(**{**data.get("runner", {}), **runner}),
            user_defined={**data.get("user_defined", {}), **user_defined},
        )

    def dict(self) -> Dict[str, Any]:
        return {
            "inventory": self.inventory.dict(),
            "ssh": self.ssh.dict(),
            "logging": self.logging.dict(),
            "core": self.core.dict(),
            "runner": self.runner.dict(),
            "user_defined": self.user_defined,
        }
