import logging
import os
from pathlib import Path

from nornir.core.configuration import Config
from nornir.plugins.inventory.simple import SimpleInventory
from nornir.plugins.inventory.ansible import AnsibleInventory
from nornir.core.deserializer.configuration import Config as ConfigDeserializer

from tests.core.deserializer import my_jinja_filters

import pytest

dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "test_configuration"
)


DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)12s - %(levelname)8s - %(funcName)10s() - %(message)s"
)


class Test(object):
    def test_config_defaults(self):
        c = ConfigDeserializer()
        assert c.dict() == {
            "inventory": {
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "options": {},
                "transform_function": "",
                "transform_function_options": {},
            },
            "ssh": {"config_file": "~/.ssh/config"},
            "logging": {
                "level": "debug",
                "file": "nornir.log",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "jinja2": {"filters": ""},
            "core": {"num_workers": 20, "raise_on_error": False},
            "user_defined": {},
        }

    def test_config_basic(self):
        c = ConfigDeserializer(
            core={"num_workers": 30},
            logging={"file": ""},
            user_defined={"my_opt": True},
        )
        assert c.dict() == {
            "inventory": {
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "options": {},
                "transform_function": "",
                "transform_function_options": {},
            },
            "ssh": {"config_file": "~/.ssh/config"},
            "logging": {
                "level": "debug",
                "file": "",
                "format": DEFAULT_LOG_FORMAT,
                "to_console": False,
                "loggers": ["nornir"],
            },
            "jinja2": {"filters": ""},
            "core": {"num_workers": 30, "raise_on_error": False},
            "user_defined": {"my_opt": True},
        }

    def test_deserialize_defaults(self):
        c = ConfigDeserializer.deserialize()
        assert isinstance(c, Config)

        assert c.core.num_workers == 20
        assert not c.core.raise_on_error
        assert c.user_defined == {}

        assert c.logging.level == logging.DEBUG
        assert c.logging.file == "nornir.log"
        assert c.logging.format == DEFAULT_LOG_FORMAT
        assert not c.logging.to_console
        assert c.logging.loggers == ["nornir"]

        assert c.ssh.config_file == str(Path("~/.ssh/config").expanduser())

        assert c.inventory.plugin == SimpleInventory
        assert c.inventory.options == {}
        assert c.inventory.transform_function is None
        assert c.inventory.transform_function_options == {}

    def test_deserialize_basic(self):
        c = ConfigDeserializer.deserialize(
            core={"num_workers": 30},
            user_defined={"my_opt": True},
            logging={"file": "", "level": "info"},
            ssh={"config_file": "~/.ssh/alt_config"},
            inventory={"plugin": "nornir.plugins.inventory.ansible.AnsibleInventory"},
        )
        assert isinstance(c, Config)

        assert c.core.num_workers == 30
        assert not c.core.raise_on_error
        assert c.user_defined == {"my_opt": True}

        assert c.logging.level == logging.INFO
        assert c.logging.file == ""
        assert c.logging.format == DEFAULT_LOG_FORMAT
        assert not c.logging.to_console
        assert c.logging.loggers == ["nornir"]

        assert c.ssh.config_file == str(Path("~/.ssh/alt_config").expanduser())

        assert c.inventory.plugin == AnsibleInventory
        assert c.inventory.options == {}
        assert c.inventory.transform_function is None
        assert c.inventory.transform_function_options == {}

    def test_jinja_filters(self):
        c = ConfigDeserializer.deserialize(
            jinja2={"filters": "tests.core.deserializer.my_jinja_filters.jinja_filters"}
        )
        assert c.jinja2.filters == my_jinja_filters.jinja_filters()

    def test_jinja_filters_error(self):
        with pytest.raises(ModuleNotFoundError):
            ConfigDeserializer.deserialize(jinja2={"filters": "asdasd.asdasd"})

    def test_configuration_file_empty(self):
        config = ConfigDeserializer.load_from_file(
            os.path.join(dir_path, "empty.yaml"), user_defined={"asd": "qwe"}
        )
        assert config.user_defined["asd"] == "qwe"
        assert config.core.num_workers == 20
        assert not config.core.raise_on_error
        assert config.inventory.plugin == SimpleInventory

    def test_configuration_file_normal(self):
        config = ConfigDeserializer.load_from_file(
            os.path.join(dir_path, "config.yaml")
        )
        assert config.core.num_workers == 10
        assert not config.core.raise_on_error
        assert config.inventory.plugin == AnsibleInventory

    def test_configuration_file_override_argument(self):
        config = ConfigDeserializer.load_from_file(
            os.path.join(dir_path, "config.yaml"),
            core={"num_workers": 20, "raise_on_error": True},
        )
        assert config.core.num_workers == 20
        assert config.core.raise_on_error

    def test_configuration_file_override_env(self):
        os.environ["NORNIR_CORE_NUM_WORKERS"] = "30"
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "1"
        os.environ["NORNIR_SSH_CONFIG_FILE"] = "/user/ssh_config"
        config = ConfigDeserializer.deserialize()
        assert config.core.num_workers == 30
        assert config.core.raise_on_error
        assert config.ssh.config_file == "/user/ssh_config"
        os.environ.pop("NORNIR_CORE_NUM_WORKERS")
        os.environ.pop("NORNIR_CORE_RAISE_ON_ERROR")
        os.environ.pop("NORNIR_SSH_CONFIG_FILE")

    def test_configuration_bool_env(self):
        os.environ["NORNIR_CORE_RAISE_ON_ERROR"] = "0"
        config = ConfigDeserializer.deserialize()
        assert config.core.num_workers == 20
        assert not config.core.raise_on_error

    def test_get_user_defined_from_file(self):
        config = ConfigDeserializer.load_from_file(
            os.path.join(dir_path, "config.yaml")
        )
        assert config.user_defined["asd"] == "qwe"
