import os

from brigade.core.configuration import Config

#  import pytest


dir_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "test_configuration"
)


class Test(object):

    def test_configuration_empty(self):
        config = Config(
            config_file=os.path.join(dir_path, "empty.yaml"),
            arg1=1,
            arg2=False,
            arg3=None,
            arg4="asd",
        )
        assert config.num_workers == 20
        assert not config.raise_on_error
        assert config.arg1 == 1
        assert config.arg2 is False
        assert config.arg3 is None
        assert config.arg4 == "asd"

    def test_configuration_normal(self):
        config = Config(
            config_file=os.path.join(dir_path, "config.yaml"),
            arg1=1,
            arg2=False,
            arg3=None,
            arg4="asd",
        )
        assert config.num_workers == 10
        assert not config.raise_on_error
        assert config.arg1 == 1
        assert config.arg2 is False
        assert config.arg3 is None
        assert config.arg4 == "asd"

    def test_configuration_normal_override_argument(self):
        config = Config(
            config_file=os.path.join(dir_path, "config.yaml"),
            num_workers=20,
            raise_on_error=True,
        )
        assert config.num_workers == 20
        assert config.raise_on_error

    def test_configuration_normal_override_env(self):
        os.environ["BRIGADE_NUM_WORKERS"] = "30"
        os.environ["BRIGADE_RAISE_ON_ERROR"] = "1"
        config = Config(config_file=os.path.join(dir_path, "config.yaml"))
        assert config.num_workers == 30
        assert config.raise_on_error
        os.environ.pop("BRIGADE_NUM_WORKERS")
        os.environ.pop("BRIGADE_RAISE_ON_ERROR")

    def test_configuration_bool_env(self):
        os.environ["BRIGADE_RAISE_ON_ERROR"] = "0"
        config = Config()
        assert config.num_workers == 20
        assert not config.raise_on_error

    def test_get_user_defined_from_file(self):
        config = Config(config_file=os.path.join(dir_path, "config.yaml"))
        assert config.get(
            "user_defined", env="USER_DEFINED", default="qweqwe"
        ) == "asdasd"

    def test_get_user_defined_from_default(self):
        config = Config()
        assert config.get(
            "user_defined", env="USER_DEFINED", default="qweqwe"
        ) == "qweqwe"

    def test_get_user_defined_from_env(self):
        os.environ["USER_DEFINED"] = "zxczxc"
        config = Config(config_file=os.path.join(dir_path, "config.yaml"))
        assert config.get(
            "user_defined", env="USER_DEFINED", default="qweqwe"
        ) == "zxczxc"
        os.environ.pop("USER_DEFINED")

    def test_get_user_defined_from_env_bool(self):
        os.environ["USER_DEFINED"] = "0"
        config = Config()
        assert not config.get("user_defined", env="USER_DEFINED", parameter_type="bool")
        os.environ.pop("USER_DEFINED")

    def test_get_user_defined_nested(self):
        config = Config(config_file=os.path.join(dir_path, "config.yaml"))
        assert config.get("user_defined", root="my_root") == "i am nested"
