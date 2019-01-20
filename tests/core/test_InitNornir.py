import logging
import logging.config
import os
import pytest

from nornir import InitNornir
from nornir.core.deserializer.inventory import Inventory


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
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "app.log",
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "standard",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
        },
    },
    "loggers": {
        "app": {"handlers": ["file", "console"], "level": "INFO", "propagate": False}
        # "": {
        #     "handlers": ["console", "default"],
        #     "level": "INFO",
        #     "propagate": False
        # }
    },
    "root": {"handlers": ["file", "console"], "level": "INFO"},
}


def transform_func(host):
    host["processed_by_transform_function"] = True


def transform_func_with_options(host, a):
    host["a"] = a


class StringInventory(Inventory):
    def __init__(self, **kwargs):
        inv_dict = {"hosts": {"host1": {}, "host2": {}}, "groups": {}, "defaults": {}}
        super().__init__(**inv_dict, **kwargs)


class Test(object):
    def test_InitNornir_defaults(self):
        os.chdir("tests/inventory_data/")
        nr = InitNornir()
        os.chdir("../../")
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 20
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_file(self):
        nr = InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 100
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_programmatically(self):
        nr = InitNornir(
            core={"num_workers": 100},
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 100
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_override_partial_section(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"raise_on_error": True},
        )
        assert nr.config.core.num_workers == 100
        assert nr.config.core.raise_on_error

    def test_InitNornir_combined(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"num_workers": 200},
        )
        assert not nr.data.dry_run
        assert nr.config.core.num_workers == 200
        assert len(nr.inventory.hosts)
        assert len(nr.inventory.groups)

    def test_InitNornir_different_inventory_by_string(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={"plugin": "tests.core.test_InitNornir.StringInventory"},
        )
        assert "host1" in nr.inventory.hosts

    def test_InitNornir_different_inventory_imported(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={"plugin": StringInventory},
        )
        assert "host1" in nr.inventory.hosts

    def test_InitNornir_different_transform_function_by_string(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": "tests.core.test_InitNornir.transform_func",
                "options": {
                    "host_file": "tests/inventory_data/hosts.yaml",
                    "group_file": "tests/inventory_data/groups.yaml",
                },
            },
        )
        for host in nr.inventory.hosts.values():
            assert host["processed_by_transform_function"]

    def test_InitNornir_different_transform_function_imported(self):
        nr = InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            inventory={
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": transform_func,
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
                "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                "transform_function": "tests.core.test_InitNornir.transform_func_with_options",
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
                    "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
                    "transform_function": "tests.core.test_InitNornir.transform_func_with_options",
                    "transform_function_options": {"a": 1, "b": 0},
                    "options": {
                        "host_file": "tests/inventory_data/hosts.yaml",
                        "group_file": "tests/inventory_data/groups.yaml",
                    },
                },
            )
            assert nr


class LoggingTest:
    def setUp(self):
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_InitNornir_logging_defaults(self):
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            core={"num_workers": 200},
        )
        root_logger = logging.getLogger()
        nornir_logger = logging.getLogger("nornir")

        assert root_logger.level == logging.WARNING
        assert not root_logger.hasHandlers()
        assert nornir_logger.level == logging.DEBUG
        assert len(nornir_logger.handlers) == 1
        assert isinstance(nornir_logger.handlers[0], logging.FileHandler)

    def test_InitNornir_logging_programmatic_console(self):
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            logging={"to_console": True},
        )
        root_logger = logging.getLogger()
        nornir_logger = logging.getLogger("nornir")

        assert root_logger.level == logging.WARNING
        assert not root_logger.hasHandlers()
        assert nornir_logger.level == logging.DEBUG
        assert len(nornir_logger.handlers) == 3
        assert any(
            isinstance(handler, logging.FileHandler)
            for handler in nornir_logger.handlers
        )
        assert any(
            isinstance(handler, logging.StreamHandler)
            for handler in nornir_logger.handlers
        )

    def test_InitNornir_logging_programmatic_disable(self):
        InitNornir(
            config_file=os.path.join(dir_path, "a_config.yaml"),
            logging={"enabled": False},
        )
        root_logger = logging.getLogger()
        nornir_logger = logging.getLogger("nornir")

        assert root_logger.level == logging.WARNING
        assert not root_logger.hasHandlers()
        assert nornir_logger.level == logging.NOTSET
        assert not nornir_logger.hasHandlers()

    def test_InitNornir_logging_basicConfig(self):
        logging.basicConfig(level="DEBUG")
        InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        nornir_logger = logging.getLogger("nornir")

        assert nornir_logger.level == logging.NOTSET
        assert not nornir_logger.hasHandlers()

    def test_InitNornir_logging_dictConfig(self):
        logging.config.dictConfig(LOGGING_DICT)
        InitNornir(config_file=os.path.join(dir_path, "a_config.yaml"))
        nornir_logger = logging.getLogger("nornir")

        assert nornir_logger.level == logging.NOTSET
        assert not nornir_logger.hasHandlers()
