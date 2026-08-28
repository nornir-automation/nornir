from __future__ import annotations

import ast
import logging
import logging.handlers
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Generic, TypeVar

import ruamel.yaml

from nornir.core.exceptions import ConflictingConfigurationWarning

DEFAULT_SSH_CONFIG = str(Path("~/.ssh/config").expanduser())

T = TypeVar("T")


class Parameter(Generic[T]):
    def __init__(
        self,
        envvar: str,
        typ: type[T] | None = None,
        help: str = "",
        default: T | None = None,
    ) -> None:
        if typ is not None:
            self.type: type[T] = typ
        elif default is not None:
            self.type = default.__class__
        else:
            raise TypeError("either typ or default needs to be specified")
        self.envvar = envvar
        self.help = help
        self.default = default or self.type()

    def resolve(self, value: T | None) -> T:
        """Resolve the value of the parameter.

        The first of these that is not ``None`` wins:

            1. ``value``, as given by the user
            2. the environment variable named by ``envvar``
            3. ``default``

        Environment variables are always strings, so they are converted to the type of
        the parameter. For a ``bool`` parameter, ``true``, ``True``, ``1`` and ``yes``
        mean ``True`` and any other non-empty value means ``False``. Types other than
        ``str`` and ``bool`` are parsed with :py:func:`ast.literal_eval`.

        Arguments:
            value: value given by the user, or ``None`` to fall back to the environment
                variable and then the default

        Returns:
            The resolved value.

        Raises:
            TypeError: the resolved value is not of the type of the parameter

        """
        v: Any | None = value
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

        if not isinstance(v, self.type):
            raise TypeError(f"Expected type {self.type}, got {type(v)}")

        return v


class SSHConfig:
    __slots__ = ("config_file",)

    class Parameters:
        config_file = Parameter[str](default=DEFAULT_SSH_CONFIG, envvar="NORNIR_SSH_CONFIG_FILE")

    def __init__(self, config_file: str | None = None) -> None:
        self.config_file = self.Parameters.config_file.resolve(config_file)

    def dict(self) -> dict[str, Any]:
        """Return the ssh configuration as a dictionary.

        Returns:
            The values in effect, after the environment variables and the defaults have
            been applied.

        """
        return {"config_file": self.config_file}


class InventoryConfig:
    __slots__ = "options", "plugin", "transform_function", "transform_function_options"

    class Parameters:
        plugin = Parameter[str](
            typ=str, default="SimpleInventory", envvar="NORNIR_INVENTORY_PLUGIN"
        )
        options = Parameter[dict[str, Any]](default={}, envvar="NORNIR_INVENTORY_OPTIONS")
        transform_function = Parameter[str](typ=str, envvar="NORNIR_INVENTORY_TRANSFORM_FUNCTION")
        transform_function_options = Parameter[dict[str, Any]](
            default={}, envvar="NORNIR_INVENTORY_TRANSFORM_FUNCTION_OPTIONS"
        )

    def __init__(
        self,
        plugin: str | None = None,
        options: dict[str, Any] | None = None,
        transform_function: str | None = None,
        transform_function_options: dict[str, Any] | None = None,
    ) -> None:
        self.plugin = self.Parameters.plugin.resolve(plugin)
        self.options = self.Parameters.options.resolve(options) or {}
        self.transform_function = self.Parameters.transform_function.resolve(transform_function)
        self.transform_function_options = self.Parameters.transform_function_options.resolve(
            transform_function_options
        )

    def dict(self) -> dict[str, Any]:
        """Return the inventory configuration as a dictionary.

        Returns:
            The values in effect, after the environment variables and the defaults have
            been applied.

        """
        return {
            "plugin": self.plugin,
            "options": self.options,
            "transform_function": self.transform_function,
            "transform_function_options": self.transform_function_options,
        }


class LoggingConfig:
    __slots__ = "enabled", "format", "level", "log_file", "loggers", "to_console"

    class Parameters:
        enabled = Parameter[bool](default=True, envvar="NORNIR_LOGGING_ENABLED")
        level = Parameter[str](default="INFO", envvar="NORNIR_LOGGING_LEVEL")
        log_file = Parameter[str](default="nornir.log", envvar="NORNIR_LOGGING_LOG_FILE")
        format = Parameter[str](
            default="%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s",
            envvar="NORNIR_LOGGING_FORMAT",
        )
        to_console = Parameter[bool](default=False, envvar="NORNIR_LOGGING_TO_CONSOLE")
        loggers = Parameter[list[str]](default=["nornir"], envvar="NORNIR_LOGGING_LOGGERS")

    def __init__(
        self,
        enabled: bool | None = None,
        level: str | None = None,
        log_file: str | None = None,
        format: str | None = None,
        to_console: bool | None = None,
        loggers: list[str] | None = None,
    ) -> None:
        self.enabled = self.Parameters.enabled.resolve(enabled)
        self.level = self.Parameters.level.resolve(level)
        self.log_file = self.Parameters.log_file.resolve(log_file)
        self.format = self.Parameters.format.resolve(format)
        self.to_console = self.Parameters.to_console.resolve(to_console)
        self.loggers = self.Parameters.loggers.resolve(loggers)

    def dict(self) -> dict[str, Any]:
        """Return the logging configuration as a dictionary.

        Returns:
            The values in effect, after the environment variables and the defaults have
            been applied.

        """
        return {
            "enabled": self.enabled,
            "level": self.level,
            "log_file": self.log_file,
            "format": self.format,
            "to_console": self.to_console,
            "loggers": self.loggers,
        }

    def configure(self) -> None:
        """Configure the loggers named in ``loggers`` from this configuration.

        Records of level ``INFO`` and below go to stdout and the rest to stderr, but
        only when ``to_console`` is set. A rotating file handler is added when
        ``log_file`` is set. Nothing happens at all when ``enabled`` is ``False``.

        Loggers that already have handlers are left untouched, so calling this more
        than once, which happens when :obj:`nornir.InitNornir` is called repeatedly,
        does not duplicate log records.

        Warns:
            nornir.core.exceptions.ConflictingConfigurationWarning: the root logger has
                already been configured elsewhere, which can lead to unexpected results

        """
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
                "https://nornir.readthedocs.io/en/stable/configuration/index.html#logging"
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


class RunnerConfig:
    __slots__ = ("options", "plugin")

    class Parameters:
        plugin = Parameter[str](default="threaded", envvar="NORNIR_RUNNER_PLUGIN")
        options = Parameter[dict[str, Any]](default={}, envvar="NORNIR_RUNNER_OPTIONS")

    def __init__(self, plugin: str | None = None, options: dict[str, Any] | None = None) -> None:
        self.plugin = self.Parameters.plugin.resolve(plugin)
        self.options = self.Parameters.options.resolve(options)

    def dict(self) -> dict[str, Any]:
        """Return the runner configuration as a dictionary.

        Returns:
            The values in effect, after the environment variables and the defaults have
            been applied.

        """
        return {
            "plugin": self.plugin,
            "options": self.options,
        }


class CoreConfig:
    __slots__ = ("raise_on_error",)

    class Parameters:
        raise_on_error = Parameter[bool](default=False, envvar="NORNIR_CORE_RAISE_ON_ERROR")

    def __init__(self, raise_on_error: bool | None = None) -> None:
        self.raise_on_error = self.Parameters.raise_on_error.resolve(raise_on_error)

    def dict(self) -> dict[str, Any]:
        """Return the core configuration as a dictionary.

        Returns:
            The values in effect, after the environment variables and the defaults have
            been applied.

        """
        return {
            "raise_on_error": self.raise_on_error,
        }


class Config:
    __slots__ = (
        "core",
        "inventory",
        "logging",
        "runner",
        "ssh",
        "user_defined",
    )

    def __init__(
        self,
        inventory: InventoryConfig | None = None,
        ssh: SSHConfig | None = None,
        logging: LoggingConfig | None = None,
        core: CoreConfig | None = None,
        runner: RunnerConfig | None = None,
        user_defined: dict[str, Any] | None = None,
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
        inventory: dict[str, Any] | None = None,
        ssh: dict[str, Any] | None = None,
        logging: dict[str, Any] | None = None,
        core: dict[str, Any] | None = None,
        runner: dict[str, Any] | None = None,
        user_defined: dict[str, Any] | None = None,
    ) -> Config:
        """Build a configuration from one dictionary per section.

        Every section is optional, and so is every key within a section: whatever is
        left out falls back to its environment variable and then to its default.

        Returns:
            :obj:`Config`: The resulting configuration.

        """
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
        inventory: dict[str, Any] | None = None,
        ssh: dict[str, Any] | None = None,
        logging: dict[str, Any] | None = None,
        core: dict[str, Any] | None = None,
        runner: dict[str, Any] | None = None,
        user_defined: dict[str, Any] | None = None,
    ) -> Config:
        """Build a configuration from a YAML file.

        The keyword arguments are merged on top of the contents of the file key by key,
        so passing one overrides that single setting and leaves the rest of its section
        as the file defined it. This is what lets
        ``InitNornir(config_file="config.yaml", core={"raise_on_error": True})`` change
        one value without restating the file.

        Arguments:
            config_file: path to the YAML file to read
            inventory: overrides for the ``inventory`` section of the file
            ssh: overrides for the ``ssh`` section of the file
            logging: overrides for the ``logging`` section of the file
            core: overrides for the ``core`` section of the file
            runner: overrides for the ``runner`` section of the file
            user_defined: overrides for the ``user_defined`` section of the file

        Returns:
            :obj:`Config`: The resulting configuration.

        """
        inventory = inventory or {}
        ssh = ssh or {}
        logging = logging or {}
        core = core or {}
        runner = runner or {}
        user_defined = user_defined or {}
        with Path(config_file).open(encoding="utf-8") as f:
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

    def dict(self) -> dict[str, Any]:
        """Return the whole configuration as a dictionary.

        Returns:
            Every section serialized as a dictionary, with the values in effect after
            the environment variables and the defaults have been applied.

        """
        return {
            "inventory": self.inventory.dict(),
            "ssh": self.ssh.dict(),
            "logging": self.logging.dict(),
            "core": self.core.dict(),
            "runner": self.runner.dict(),
            "user_defined": self.user_defined,
        }
