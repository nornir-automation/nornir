import importlib
import os
from typing import Any, Callable, Dict, List, Optional


import yaml


class Config(object):
    """
    Arguments:
        inventory: Path to inventory modules
        jinja_filters: Path to callable returning jinja filters to be used
        logging_dictConfig: Configuration dictionary schema supported by the logging subsystem.
        logging_format:
        logging_level: Logging level. Can be any supported level by the logging subsystem
        logging_loggers: List of loggers to configure. This allows you to enable logging for
            multiple loggers. For instance, you could enable logging for both nornir and paramiko
            or just for paramiko. An empty list will enable logging for
        logging_to_console: Whether to log to stdout or not
        num_workers: description": "Number of Nornir worker processes that are run at the same time,
            configuration can be overridden on individual tasks by using the `num_workers`
            argument to (:obj:`nornir.core.Nornir.run`)
        transform_function: Path to transform function. The transform_function you provide
            will run against each host in the inventory. This is useful to manipulate host
            data and make it more consumable. For instance, if your inventory has a 'user'
        raise_on_error: If set to ``True``, (:obj:`nornir.core.Nornir.run`) method of will raise
            an exception if at least a host failed
        ssh_config_file: User ssh_config_file
    """

    class Defaults(object):
        inventory = "nornir.plugins.inventory.simple.SimpleInventory"
        jinja_filters = ""
        logging_dictConfig: Dict[str, Any] = {}
        logging_file = "nornir.log"
        logging_format = (
            "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s"
        )
        logging_level = "debug"
        logging_loggers = ["nornir"]
        logging_to_console = False
        num_workers = 20
        raise_on_error = False
        ssh_config_file = os.path.join(os.path.expanduser("~"), ".ssh", "config")
        transform_function = ""

    __slots__ = (
        "_raw_config",
        "inventory",
        "jinja_filters",
        "num_workers",
        "logging_dictConfig",
        "logging_file",
        "logging_format",
        "logging_level",
        "logging_loggers",
        "logging_to_console",
        "raise_on_error",
        "ssh_config_file",
        "transform_function",
    )

    def __init__(
        self, config_file: Optional[str] = None, **kwargs: Optional[Dict[str, Any]]
    ) -> None:
        self._raw_config: Dict[str, Any] = self._parse_config(config_file, **kwargs)

        self.inventory: str = (
            str(self._raw_config.get("inventory", Config.Defaults.inventory))
        )
        self.jinja_filters: str = (
            str(self._raw_config.get("jinja_filters", Config.Defaults.jinja_filters))
        )
        self.logging_dictConfig: Dict[str, Any] = (
            dict(
                self._raw_config.get(
                    "logging_dictConfig", Config.Defaults.logging_dictConfig
                )
            )
        )
        self.logging_file: str = (
            str(self._raw_config.get("logging_file", Config.Defaults.logging_file))
        )
        self.logging_format: str = (
            str(self._raw_config.get("logging_format", Config.Defaults.logging_format))
        )
        self.logging_level: str = (
            str(self._raw_config.get("logging_level", Config.Defaults.logging_level))
        )
        self.logging_loggers: List[str] = (
            list(
                self._raw_config.get("logging_loggers", Config.Defaults.logging_loggers)
            )
        )
        self.logging_to_console: bool = (
            bool(
                self._raw_config.get(
                    "logging_to_console", Config.Defaults.logging_to_console
                )
            )
        )
        self.num_workers: int = (
            int(self._raw_config.get("num_workers", Config.Defaults.num_workers))
        )
        self.raise_on_error: bool = (
            bool(self._raw_config.get("raise_on_error", Config.Defaults.raise_on_error))
        )
        self.transform_function: str = (
            str(
                self._raw_config.get(
                    "transform_function", Config.Defaults.transform_function
                )
            )
        )

    def _parse_config(
        self, config_file: Optional[str], **kwargs: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if config_file:
            with open(config_file, "r") as f:
                result = yaml.load(f.read()) or {}

        result.update(kwargs)

        for k in self.__slots__:
            if not k.startswith("_"):
                v = os.environ.get(f"BRIGADE_{k.upper()}")
                if v:
                    result[k] = v
        return result

    def _resolve_import_from_string(self, import_path: str) -> Callable[..., Any]:
        """
        Resolves import from a string. Checks if callable or path is given.

        Arguments:
            import_path(str): path of the import
        """
        module_name = ".".join(import_path.split(".")[:-1])
        obj_name = import_path.split(".")[-1]
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
