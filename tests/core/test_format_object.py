from brigade.core.helpers import format_object


kwargs = {
    "extra_key1": "extra_value1",
}


class Test(object):

    def test_format_object_string(self, brigade):
        host = brigade.inventory.hosts["dev1.group_1"]
        obj = "{name} - {my_var} - {extra_key1}"
        result = format_object(obj, host, **kwargs)
        assert result == "dev1.group_1 - comes_from_dev1.group_1 - extra_value1"

    def test_format_object_list(self, brigade):
        host = brigade.inventory.hosts["dev1.group_1"]
        obj = [1, "asdasd", "{name}", "{my_var}", "{extra_key1}"]
        result = format_object(obj, host, **kwargs)
        assert result == [1, "asdasd", "dev1.group_1", "comes_from_dev1.group_1", "extra_value1"]

    def test_format_object_dict(self, brigade):
        host = brigade.inventory.hosts["dev1.group_1"]
        obj = {
            1: "asdasd",
            "{name}": "{my_var}",
            "test": "{extra_key1}"
        }
        result = format_object(obj, host, **kwargs)
        assert result == {1: 'asdasd', 'dev1.group_1': 'comes_from_dev1.group_1',
                          'test': 'extra_value1'}

    def test_format_object_complex(self, brigade):
        host = brigade.inventory.hosts["dev1.group_1"]
        obj = {
            1: ["{name}", {"{name}": "test"}],
            "{name}": "{my_var}",
            "test": "{extra_key1}"
        }
        result = format_object(obj, host, **kwargs)
        assert result == {1: ['dev1.group_1', {'dev1.group_1': 'test'}],
                          'dev1.group_1': 'comes_from_dev1.group_1',
                          'test': 'extra_value1'}
