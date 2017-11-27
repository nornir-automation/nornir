from brigade.core.exceptions import BrigadeExecutionError, FileError
from brigade.plugins.tasks import data
import yaml
import os
import pytest


data_dir = '{}/test_data'.format(os.path.dirname(os.path.realpath(__file__)))


class Test(object):

    def test_load_yaml(self, brigade):
        test_file = '{}/simple.yaml'.format(data_dir)
        result = brigade.run(data.load_yaml,
                             file=test_file)

        for h, r in result.items():
            d = r.result
            assert d['env'] == 'test'
            assert d['services'] == ['dhcp', 'dns']

    def test_load_yaml_error_broken_file(self, brigade):
        test_file = '{}/broken.yaml'.format(data_dir)
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(data.load_yaml,
                        file=test_file)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, yaml.YAMLError)

    def test_load_yaml_error_missing_file(self, brigade):
        test_file = '{}/missing.yaml'.format(data_dir)
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(data.load_yaml,
                        file=test_file)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, FileError)
