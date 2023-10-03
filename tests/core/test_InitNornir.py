import logging
import logging.config
import os

import pytest

from nornir import InitNornir
from nornir.core.exceptions import ConflictingConfigurationWarning
from nornir.core.inventory import Defaults, Group, Groups, Host, Hosts, Inventory
from nornir.core.plugins.inventory import (
    InventoryPluginRegister,
    TransformFunctionRegister,
)

dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_InitNornir")

LOGGING_DICT = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)-8s {%(name)s:%(lineno)d} %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
        }
    },
    "loggers": {
        "app": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "nornir": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
}


def transform_func(host):
    host["processed_by_transform_function"] = True


def transform_func_with_options(host, a):
    host["a"] = a


class InventoryTest:
    def __init__(self, *args, **kwargs):
        pass

    def load(self):
        return Inventory(
            hosts=Hosts({"h1": Host("h1"), "h2": Host("h2"), "h3": Host("h3")}),
            groups=Groups({"g1": Group("g1")}),
            defaults=Defaults(),
        )


InventoryPluginRegister.register("inventory-test", InventoryTest)
TransformFunctionRegister.register("transform_func", transform_func)
TransformFunctionRegister.register(
    "transform_func_with_options", transform_func_with_options
)


class Test(object):
    def test_InitNornir_bare(self):
        os.chdir("tests/inventory_data/")
        nr = InitNornir()
        os.chdir("../../")
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_defaults(self):
        os.chdir("tests/inventory_data/")
        nr = InitNornir(inventory={"plugin": "inventory-test"})
        os.chdir("../../")
        assert not nr.data.dry_run
        assert not nr.config.core.raise_on_error
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_file(self):
        nr = InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not nr.data.dry_run
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_programmatically(self):
        nr = InitNornir(
            core={"raise_on_error": True},
            inventory={
                "plugin": "inventory-test",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        assert not nr.data.dry_run
        assert nr.config.core.raise_on_error
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_override_partial_section(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"raise_on_error": True},
        )
        assert nr.config.core.raise_on_error

    def test_InitNornir_combined(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"raise_on_error": True},
        )
        assert not nr.data.dry_run
        assert nr.config.core.raise_on_error
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_different_transform_function_by_string(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "inventory-test",
                "transform_function": "transform_func",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["processed_by_transform_function"]

    def test_InitNornir_different_transform_function_by_string_with_options(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "inventory-test",
                "transform_function": "transform_func_with_options",
                "transform_function_options": {"a": 1},
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["a"] == 1

    def test_InitNornir_different_transform_function_by_string_with_bad_options(self):
        with pytest.raises(TypeError):
            nr = InitNornir(
                config_file=os.path.join(dir_path, "a_config.yaml"),
                inventory={
                    "plugin": "inventory-test",
                    "transform_function": "transform_func_with_options",
                    "transform_function_options": {"a": 1, "b": 0},
                    "options": {
                        "host_file": "tests/inventory_data/hosts.yaml",
                        "group_file": "tests/inventory_data/groups.yaml",
                    },
                },
            )
            assert nr


class TestLogging:
    @classmethod
    def cleanup(cls):
        # this does not work as setup_method, because pytest injects
        # _pytest.logging.LogCaptureHandler handler to the root logger
        # and StreamHandler to _pytest.capture.EncodedFile to other loggers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

        for logger_name in ["nornir", "app"]:
            logger_ = logging.getLogger(logger_name)
            for handler in logger_.handlers:
                logger_.removeHandler(handler)
            logger_.setLevel(logging.NOTSET)

    @classmethod
    def teardown_class(cls):
        cls.cleanup()

    def test_InitNornir_logging_defaults(self):
        self.cleanup()
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
        )
        nornir_logger = logging.getLogger("nornir")

        assert nornir_logger.level == logging.INFO
        assert len(nornir_logger.handlers) == 1
        assert isinstance(nornir_logger.handlers[0], logging.FileHandler)

    def test_InitNornir_logging_to_console(self):
        self.cleanup()
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            logging={"to_console": True},
        )
        nornir_logger = logging.getLogger("nornir")

        assert nornir_logger.level == logging.INFO
        assert len(nornir_logger.handlers) == 3
        assert any(
            isinstance(handler, logging.FileHandler)
            for handler in nornir_logger.handlers
        )
        assert any(
            isinstance(handler, logging.StreamHandler)
            for handler in nornir_logger.handlers
        )

    def test_InitNornir_logging_disabled(self):
        self.cleanup()
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            logging={"enabled": False},
        )
        nornir_logger = logging.getLogger("nornir")

        assert nornir_logger.level == logging.NOTSET

    def test_InitNornir_logging_basicConfig(self):
        self.cleanup()
        logging.basicConfig()
        with pytest.warns(ConflictingConfigurationWarning):
            InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        nornir_logger = logging.getLogger("nornir")

        assert logging.getLogger().hasHandlers()
        assert nornir_logger.level == logging.INFO
        assert nornir_logger.hasHandlers()

    def test_InitNornir_logging_dictConfig(self):
        self.cleanup()
        logging.config.dictConfig(LOGGING_DICT)
        with pytest.warns(ConflictingConfigurationWarning):
            InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))

        nornir_logger = logging.getLogger("nornir")
        root_logger = logging.getLogger()
        app_logger = logging.getLogger("app")

        assert root_logger.hasHandlers()
        assert root_logger.level == logging.DEBUG
        assert nornir_logger.hasHandlers()
        assert app_logger.level == logging.INFO
