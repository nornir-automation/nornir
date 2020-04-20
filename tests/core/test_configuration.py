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
            "core": {"num_workers": 20, "raise_on_error": False},
            "inventory": {
                "plugin": "",
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
            "core": {"num_workers": 20, "raise_on_error": False},
            "inventory": {
                "plugin": "",
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
            core={"num_workers": 30},
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
            "ssh": {"config_file": str(Path("~/.ssh/config").expanduser())},
            "logging": {
                "enabled": True,
                "level": "INFO",
                "log_file": "",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "core": {"num_workers": 30, "raise_on_error": False},
            "user_defined": {"my_opt": True},
        }

    def test_configuration_file_override_argument(self):
        config = Config.from_file(
            os.path.join(dir_path, "config.yaml"),
            core={"num_workers": 20, "raise_on_error": True},
        )
        assert config.core.num_workers == 20
        assert config.core.raise_on_error

    def test_configuration_file_override_env(self):
        os.environ["NORNIR_CORE_NUM_WORKERS"] = "30"
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "1"
        os.environ["NORNIR_SSH_CONFIG_FILE"] = "/user/ssh_config"
        config = Config.from_dict(inventory={"plugin": "an-inventory"})
        assert config.core.num_workers == 30
        assert config.core.raise_on_error
        assert config.ssh.config_file == "/user/ssh_config"
        os.environ.pop("NORNIR_CORE_NUM_WORKERS")
        os.environ.pop("NORNIR_CORE_RAISE_ON_ERROR")
        os.environ.pop("NORNIR_SSH_CONFIG_FILE")

    def test_configuration_bool_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "0"
        config = Config.from_dict(inventory={"plugin": "an-inventory"})
        assert config.core.num_workers == 20
        assert not config.core.raise_on_error

    def test_get_user_defined_from_file(self):
        config = Config.from_file(os.path.join(dir_path, "config.yaml"))
        assert config.user_defined["asd"] == "qwe"

    def test_order_of_resolution_config_is_lowest(self):
        config = Config.from_file(os.path.join(dir_path, "config.yaml"))
        assert config.core.num_workers == 10

    def test_order_of_resolution_code_is_higher_than_env(self):
        os.environ["NORNIR_CORE_NUM_WORKERS"] = "20"
        config = Config.from_file(
            os.path.join(dir_path, "config.yaml"), core={"num_workers": 30}
        )
        os.environ.pop("NORNIR_CORE_NUM_WORKERS")
        assert config.core.num_workers == 30
