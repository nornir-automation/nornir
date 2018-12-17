import os


from nornir.plugins.tasks import text

from jinja2 import TemplateSyntaxError


data_dir = "{}/test_data".format(os.path.dirname(os.path.realpath(__file__)))


class Test(object):
    def test_template_file(self, nornir):
        result = nornir.run(
            text.template_file, template="simple.j2", my_var="asd", path=data_dir
        )

        assert result
        for h, r in result.items():
            assert h in r.result
            if h == "host3.group_2":
                assert "my_var: comes_from_all" in r.result
            if h == "host4.group_2":
                assert "my_var: comes_from_host4.group_2" in r.result

    def test_template_file_error_broken_file(self, nornir):
        results = nornir.run(text.template_file, template="broken.j2", path=data_dir)
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, TemplateSyntaxError)
        assert processed
