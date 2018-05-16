import importlib
import os


import yaml


CONF = {
    "inventory": {
        "description": "Path to inventory modules.",
        "type": "str",
        "default": "nornir.plugins.inventory.simple.SimpleInventory",
    },
    "transform_function": {
        "description": "Path to transform function. The transform_function you provide "
        "will run against each host in the inventory. This is useful to manipulate host "
        "data and make it more consumable. For instance, if your inventory has a 'user' "
        "attribute you could use this function to map it to 'nornir_user'",
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
    "logging_dictConfig": {
        "description": "Configuration dictionary schema supported by the logging subsystem. "
        "Overrides rest of logging_* parameters.",
        "type": "dict",
        "default": {},
    },
    "logging_level": {
        "description": "Logging level. Can be any supported level by the logging subsystem",
        "type": "str",
        "default": "debug",
    },
    "logging_file": {
        "description": "Logging file. Empty string disables logging to file.",
        "type": "str",
        "default": "nornir.log",
    },
    "logging_format": {
        "description": "Logging format",
        "type": "str",
        "default": "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s",
    },
    "logging_to_console": {
        "description": "Whether to log to stdout or not.",
        "type": "bool",
        "default": False,
    },
    "logging_loggers": {
        "description": "List of loggers to configure. This allows you to enable logging for "
        "multiple loggers. For instance, you could enable logging for both nornir "
        "and paramiko or just for paramiko. An empty list will enable logging for "
        "all loggers.",
        "type": "list",
        "default": ["nornir"],
    },
}

types = {"int": int, "str": str}


class Config:
    """
    This object handles the configuration of Nornir.

    Arguments:
        config_file(``str``): Yaml configuration file.
    """

    def __init__(self, config_file=None, **kwargs):
        if config_file:
            with open(config_file, "r") as f:
                data = yaml.load(f.read()) or {}
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

        callable = ["jinja_filters"]
        for c in callable:
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
