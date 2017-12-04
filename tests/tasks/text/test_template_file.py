import os


from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import text

from jinja2 import TemplateSyntaxError

import pytest


data_dir = '{}/test_data'.format(os.path.dirname(os.path.realpath(__file__)))


class Test(object):

    def test_template_file(self, brigade):
        result = brigade.run(text.template_file,
                             template='simple.j2',
                             path=data_dir)

        assert result
        for h, r in result.items():
            assert h in r.result
            if h == 'host3.group_2':
                assert 'my_var: comes_from_all' in r.result
            if h == 'host4.group_2':
                assert 'my_var: comes_from_host4.group_2' in r.result

    def test_template_file_error_broken_file(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(text.template_file,
                        template='broken.j2',
                        path=data_dir)
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, TemplateSyntaxError)
