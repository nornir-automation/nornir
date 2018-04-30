import os
import logging

from brigade.plugins.functions.text import print_result
from brigade.plugins.functions.text import print_title
from brigade.plugins.tasks.data import load_yaml
from brigade.core.task import Result
from tests.wrapper import wrap_cli_test

data_dir = "{}/test_data".format(os.path.dirname(os.path.realpath(__file__)))
output_dir = "{}/output_data".format(os.path.dirname(os.path.realpath(__file__)))


def echo_task(task, msg="Brigade"):
    return Result(
        host=task.host,
        result="Hello from {}".format(msg),
        output="Hello from {}".format(msg),
    )


def data_with_greeting(task):
    task.run(task=echo_task)
    task.run(task=load_yaml, file="{}/sample.yaml".format(data_dir))


def parse_data(task):
    r = task.run(
        task=load_yaml,
        file="{}/{}.yaml".format(data_dir, task.host),
        severity_level=logging.WARN,
    )
    if r.result["failed"]:
        raise Exception("Unknown Error -> Contact your system administrator")

    return Result(host=task.host, changed=r.result["changed"])


def read_data(task):
    task.run(task=echo_task, severity_level=logging.DEBUG)
    task.run(task=echo_task, msg="CRITICAL", severity_level=logging.CRITICAL)
    task.run(task=parse_data, severity_level=logging.WARN)


class Test(object):

    @wrap_cli_test(output="{}/basic_single".format(output_dir))
    def test_print_basic(self, brigade):
        filter = brigade.filter(name="dev1.group_1")
        result = filter.run(echo_task)
        print_result(result, vars="result")

    @wrap_cli_test(output="{}/basic_inventory".format(output_dir))
    def test_print_basic_inventory(self, brigade):
        result = brigade.run(echo_task)
        print_result(result)

    @wrap_cli_test(output="{}/basic_inventory_one_host".format(output_dir))
    def test_print_basic_inventory_one_host(self, brigade):
        result = brigade.run(data_with_greeting)
        print_result(result["dev2.group_1"])

    @wrap_cli_test(output="{}/basic_inventory_one_task".format(output_dir))
    def test_print_basic_inventory_one_host(self, brigade):
        result = brigade.run(data_with_greeting)
        print_result(result["dev2.group_1"][1])

    @wrap_cli_test(output="{}/multiple_tasks".format(output_dir))
    def test_print_multiple_tasks(self, brigade):
        result = brigade.run(data_with_greeting)
        print_title("Behold the data!")
        print_result(result)

    @wrap_cli_test(output="{}/changed_host".format(output_dir))
    def test_print_changed_host(self, brigade):
        filter = brigade.filter(site="site1")
        result = filter.run(read_data, severity_level=logging.WARN)
        print_result(result)

    @wrap_cli_test(output="{}/failed_with_severity".format(output_dir))
    def test_print_failed_with_severity(self, brigade):
        result = brigade.run(read_data)
        print_result(result, vars=["exception", "output"], severity_level=logging.ERROR)
