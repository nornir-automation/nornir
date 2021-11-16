import os
from pathlib import Path

from nornir.core.configuration import Config


dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "test_configuration"
)


DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s"
)


class Test(object):
    def test_config_defaults(self):
        c = Config()
        assert c.dict() == {
            "core": {"raise_on_error": False},
            "runner": {"options": {}, "plugin": "threaded"},
            "inventory": {
                "plugin": "SimpleInventory",
                "options": {},
                "transform_function": "",
                "transform_function_options": {},
            },
            "ssh": {"config_file": str(Path("~/.ssh/config").expanduser())},
            "logging": {
                "enabled": True,
                "level": "INFO",
                "log_file": "nornir.log",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "user_defined": {},
        }

    def test_config_from_dict_defaults(self):
        c = Config.from_dict()
        assert c.dict() == {
            "core": {"raise_on_error": False},
            "runner": {"options": {}, "plugin": "threaded"},
            "inventory": {
                "plugin": "SimpleInventory",
                "options": {},
                "transform_function": "",
                "transform_function_options": {},
            },
            "ssh": {"config_file": str(Path("~/.ssh/config").expanduser())},
            "logging": {
                "enabled": True,
                "level": "INFO",
                "log_file": "nornir.log",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "user_defined": {},
        }

    def test_config_basic(self):
        c = Config.from_dict(
            inventory={"plugin": "an-inventory"},
            runner={"plugin": "serial", "options": {"a": 1, "b": 2}},
            logging={"log_file": ""},
            user_defined={"my_opt": True},
        )
        assert c.dict() == {
            "inventory": {
                "plugin": "an-inventory",
                "options": {},
                "transform_function": "",
                "transform_function_options": {},
            },
            "runner": {"options": {"a": 1, "b": 2}, "plugin": "serial"},
            "ssh": {"config_file": str(Path("~/.ssh/config").expanduser())},
            "logging": {
                "enabled": True,
                "level": "INFO",
                "log_file": "",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "core": {"raise_on_error": False},
            "user_defined": {"my_opt": True},
        }

    def test_configuration_file_override_argument(self):
        config = Config.from_file(
            os.path.join(dir_path, "config.yaml"),
            core={"raise_on_error": True},
        )
        assert config.core.raise_on_error

    def test_configuration_file_override_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "1"
        os.environ["NORNIR_SSH_CONFIG_FILE"] = "/user/ssh_config"
        config = Config.from_dict(inventory={"plugin": "an-inventory"})
        assert config.core.raise_on_error
        assert config.ssh.config_file == "/user/ssh_config"
        os.environ.pop("NORNIR_CORE_RAISE_ON_ERROR")
        os.environ.pop("NORNIR_SSH_CONFIG_FILE")

    def test_configuration_bool_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "0"
        config = Config.from_dict(inventory={"plugin": "an-inventory"})
        assert not config.core.raise_on_error

    def test_get_user_defined_from_file(self):
        config = Config.from_file(os.path.join(dir_path, "config.yaml"))
        assert config.user_defined["asd"] == "qwe"

    def test_order_of_resolution_config_higher_than_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "1"
        config = Config.from_file(os.path.join(dir_path, "config.yaml"))
        os.environ.pop("NORNIR_CORE_RAISE_ON_ERROR")
        assert config.core.raise_on_error is False

    def test_order_of_resolution_code_is_higher_than_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "0"
        config = Config.from_file(
            os.path.join(dir_path, "config.yaml"), core={"raise_on_error": True}
        )
        os.environ.pop("NORNIR_CORE_RAISE_ON_ERROR")
        assert config.core.raise_on_error is True
