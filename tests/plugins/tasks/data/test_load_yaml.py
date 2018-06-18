import os
import sys
from collections import OrderedDict


from nornir.plugins.tasks import data


from ruamel.yaml.scanner import ScannerError


data_dir = "{}/test_data".format(os.path.dirname(os.path.realpath(__file__)))


class Test(object):

    def test_load_yaml(self, nornir):
        test_file = "{}/simple.yaml".format(data_dir)
        result = nornir.run(data.load_yaml, file=test_file)

        for h, r in result.items():
            d = r.result
            assert d["env"] == "test"
            assert d["services"] == ["dhcp", "dns"]
            assert isinstance(d["a_dict"], dict)

    def test_load_yaml_ordered_dict(self, nornir):
        test_file = "{}/simple.yaml".format(data_dir)
        result = nornir.run(data.load_yaml, file=test_file, ordered_dict=True)

        for h, r in result.items():
            d = r.result
            assert d["env"] == "test"
            assert d["services"] == ["dhcp", "dns"]
            assert isinstance(d["a_dict"], OrderedDict)

    def test_load_yaml_error_broken_file(self, nornir):
        test_file = "{}/broken.yaml".format(data_dir)
        results = nornir.run(data.load_yaml, file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ScannerError)
        assert processed
        nornir.data.reset_failed_hosts()

    def test_load_yaml_error_missing_file(self, nornir):
        test_file = "{}/missing.yaml".format(data_dir)

        if sys.version_info.major == 2:
            not_found = IOError
        else:
            not_found = FileNotFoundError  # noqa

        results = nornir.run(data.load_yaml, file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, not_found)
        assert processed
        nornir.data.reset_failed_hosts()
