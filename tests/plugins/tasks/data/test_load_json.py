import os
import sys

from brigade.plugins.tasks import data


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
        results = brigade.run(data.load_json,
                              file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ValueError)
        assert processed
        brigade.data.reset_failed_hosts()

    def test_load_json_error_missing_file(self, brigade):
        test_file = '{}/missing.json'.format(data_dir)
        if sys.version_info.major == 2:
            not_found = IOError
        else:
            not_found = FileNotFoundError # noqa

        results = brigade.run(data.load_json,
                              file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, not_found)
        assert processed
        brigade.data.reset_failed_hosts()
