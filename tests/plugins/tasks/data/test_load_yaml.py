import os

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

    def test_load_yaml_error_broken_file(self, nornir):
        test_file = "{}/broken.yaml".format(data_dir)
        results = nornir.run(data.load_yaml, file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ScannerError)
        assert processed

    def test_load_yaml_error_missing_file(self, nornir):
        test_file = "{}/missing.yaml".format(data_dir)
        results = nornir.run(data.load_yaml, file=test_file)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, FileNotFoundError)
        assert processed
