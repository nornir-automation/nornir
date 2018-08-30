import importlib
import logging
import os

import ruamel.yaml

logger = logging.getLogger(__name__)


CONF = {
    "inventory": {
        "description": "Path to inventory modules.",
        "type": "str",
        "default": "nornir.plugins.inventory.simple.SimpleInventory",
    },
    "transform_function": {
        "description": "Path to transform function. The transform_function you provide "
        "will run against each host in the inventory.",
        "type": "str",
        "default": {},
    },
    "jinja_filters": {
        "description": "Path to callable returning jinja filters to be used.",
        "type": "str",
        "default": {},
    },
    "num_workers": {
        "description": "Number of Nornir worker processes that are run at the same time, "
        "configuration can be overridden on individual tasks by using the "
        "`num_workers` argument to (:obj:`nornir.core.Nornir.run`)",
        "type": "int",
        "default": 20,
    },
    "raise_on_error": {
        "description": "If set to ``True``, (:obj:`nornir.core.Nornir.run`) method of will raise "
        "an exception if at least a host failed.",
        "type": "bool",
        "default": False,
    },
    "ssh_config_file": {
        "description": "User ssh_config_file",
        "type": "str",
        "default": os.path.join(os.path.expanduser("~"), ".ssh", "config"),
        "default_doc": "~/.ssh/config",
    },
    "logging_enabled": {
        "description": (
            "Whether nornir should configure logging. Manual logging "
            "configuration using dictConfig overrides these settings. "
            "Default - True"
        ),
        "type": "bool",
        "default": True,
    },
    "logging_level": {
        "description": "Logging level. Can be any supported level by the logging subsystem",
        "type": "str",
        "default": "INFO",
    },
    "logging_file": {
        "description": "Logging file. Empty string disables logging to file.",
        "type": "str",
        "default": "nornir.log",
    },
    "logging_format": {
        "description": "Logging format",
        "type": "str",
        "default": "[%(asctime)s] %(levelname)-8s {%(name)s:%(lineno)d} %(message)s",
    },
    "logging_to_console": {
        "description": "Whether to log to stdout or not.",
        "type": "bool",
        "default": False,
    },
}

types = {"int": int, "str": str}


class Config(object):
    """
    This object handles the configuration of Nornir.

    Arguments:
        config_file(``str``): Yaml configuration file.
    """

    def __init__(self, config_file=None, **kwargs):
        if config_file:
            with open(config_file, "r") as f:
                logging.debug("Reading config from %s", config_file)
                yml = ruamel.yaml.YAML(typ="safe")
                data = yml.load(f) or {}
        else:
            data = {}

        for parameter, param_conf in CONF.items():
            self._assign_property(parameter, param_conf, data)

        for k, v in data.items():
            if k not in CONF:
                setattr(self, k, v)

        for k, v in kwargs.items():
            setattr(self, k, v)

        resolve_imports = ["inventory", "transform_function", "jinja_filters"]
        for r in resolve_imports:
            obj = self._resolve_import_from_string(kwargs.get(r, getattr(self, r)))
            setattr(self, r, obj)

        callable_func = ["jinja_filters"]
        for c in callable_func:
            func = getattr(self, c)
            if func:
                setattr(self, c, func())

    def string_to_bool(self, v):
        if v.lower() in ["false", "no", "n", "off", "0"]:
            return False

        else:
            return True

    def _assign_property(self, parameter, param_conf, data):
        v = None
        if param_conf["type"] in ("bool", "int", "str"):
            env = param_conf.get("env") or "BRIGADE_" + parameter.upper()
            v = os.environ.get(env)
        if v is None:
            v = data.get(parameter, param_conf["default"])
        else:
            if param_conf["type"] == "bool":
                v = self.string_to_bool(v)
            else:
                v = types[param_conf["type"]](v)
        setattr(self, parameter, v)

    def get(self, parameter, env=None, default=None, parameter_type="str", root=""):
        """
        Retrieve a custom parameter from the configuration.

        Arguments:
            parameter(str): Name of the parameter to retrieve
            env(str): Environment variable name to retrieve the object from
            default: default value in case no parameter is found
            parameter_type(str): if a value is found cast the variable to this type
            root(str): parent key in the configuration file where to look for the parameter
        """
        value = os.environ.get(env) if env else None
        if value is None:
            if root:
                d = getattr(self, root, {})
                value = d.get(parameter, default)
            else:
                value = getattr(self, parameter, default)
        if parameter_type in [bool, "bool"]:
            if not isinstance(value, bool):
                value = self.string_to_bool(value)
        else:
            value = types[str(parameter_type)](value)
        return value

    def _resolve_import_from_string(self, import_path):
        """
        Resolves import from a string. Checks if callable or path is given.

        Arguments:
            import_path(str): path of the import
        """
        if not import_path or callable(import_path):
            return import_path

        module_name = ".".join(import_path.split(".")[:-1])
        obj_name = import_path.split(".")[-1]
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
