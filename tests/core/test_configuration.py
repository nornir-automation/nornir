import os

from nornir.core.configuration import Config
from nornir.plugins.inventory.simple import SimpleInventory

#  import pytest


dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "test_configuration"
)


class Test(object):
    def test_configuration_empty(self):
        config = Config(
            os.path.join(dir_path, "empty.yaml"), user_defined={"asd": "qwe"}
        )
        assert config.user_defined["asd"] == "qwe"
        assert config.num_workers == 20
        assert not config.raise_on_error
        assert (
            config.inventory.plugin == "nornir.plugins.inventory.simple.SimpleInventory"
        )
        assert config.inventory.get_plugin() == SimpleInventory

    def test_configuration_normal(self):
        config = Config(os.path.join(dir_path, "config.yaml"))
        assert config.num_workers == 10
        assert not config.raise_on_error
        assert config.inventory.plugin == "something"

    def test_configuration_normal_override_argument(self):
        config = Config(
            os.path.join(dir_path, "config.yaml"), num_workers=20, raise_on_error=True
        )
        assert config.num_workers == 20
        assert config.raise_on_error

    def test_configuration_normal_override_env(self):
        os.environ["NORNIR_NUM_WORKERS"] = "30"
        os.environ["NORNIR_RAISE_ON_ERROR"] = "1"
        os.environ["NORNIR_SSH_CONFIG_FILE"] = "/user/ssh_config"
        config = Config()
        assert config.num_workers == 30
        assert config.raise_on_error
        assert config.ssh.config_file == "/user/ssh_config"
        os.environ.pop("NORNIR_NUM_WORKERS")
        os.environ.pop("NORNIR_RAISE_ON_ERROR")
        os.environ.pop("NORNIR_SSH_CONFIG_FILE")

    def test_configuration_bool_env(self):
        os.environ["NORNIR_RAISE_ON_ERROR"] = "0"
        config = Config()
        assert config.num_workers == 20
        assert not config.raise_on_error

    def test_get_user_defined_from_file(self):
        config = Config(os.path.join(dir_path, "config.yaml"))
        assert config.user_defined["asd"] == "qwe"
