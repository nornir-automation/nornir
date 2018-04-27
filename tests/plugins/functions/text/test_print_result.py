from brigade.plugins.functions.text import print_result
from brigade.core.task import Result
from tests.wrapper import wrap_cli_test


def echo_task(task):
    return Result(host=task.host, result="Hello from Brigade")


class Test(object):

    @wrap_cli_test(output="tests/plugins/functions/text/test_data/output")
    def test_print_output(self, brigade):
        filter = brigade.filter(name="dev1.group_1")
        result = filter.run(echo_task)
        print_result(result)
