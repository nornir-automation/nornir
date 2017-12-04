import os


from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import text

from jinja2 import TemplateSyntaxError


import pytest


data_dir = '{}/test_data'.format(os.path.dirname(os.path.realpath(__file__)))

simple_j2 = '''

host-name: {{ host }}

my_var: {{ my_var}}

'''

broken_j2 = '''
#Broken template

host-name {{ host

my_var: {{ my_var}}
'''


class Test(object):

    def test_template_string(self, brigade):

        result = brigade.run(text.template_string,
                             template=simple_j2)

        assert result
        for h, r in result.items():
            assert 'host-name: {}'.format(h) in r.result
            if h == 'host1.group_1':
                assert 'my_var: comes_from_host1.group_1' in r.result
            if h == 'host2.group_1':
                assert 'my_var: comes_from_group_1' in r.result

    def test_template_string_error_broken_string(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(text.template_string,
                        template=broken_j2)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, TemplateSyntaxError)
