import os
import sys

from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import data


import pytest


data_dir = '{}/test_data'.format(os.path.dirname(os.path.realpath(__file__)))


class Test(object):

    def test_load_json(self, brigade):
        test_file = '{}/simple.json'.format(data_dir)
        result = brigade.run(data.load_json,
                             file=test_file)

        for h, r in result.items():
            d = r.result
            assert d['env'] == 'test'
            assert d['services'] == ['dhcp', 'dns']

    def test_load_json_error_broken_file(self, brigade):
        test_file = '{}/broken.json'.format(data_dir)
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(data.load_json,
                        file=test_file)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, ValueError)

    def test_load_json_error_missing_file(self, brigade):
        test_file = '{}/missing.json'.format(data_dir)
        if sys.version_info.major == 2:
            not_found = IOError
        else:
            not_found = FileNotFoundError # noqa

        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(data.load_json,
                        file=test_file)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, not_found)
