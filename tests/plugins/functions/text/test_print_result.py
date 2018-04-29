import os
import logging

from brigade.plugins.functions.text import print_result
from brigade.plugins.functions.text import print_title
from brigade.plugins.tasks.data import load_yaml
from brigade.core.task import Result
from tests.wrapper import wrap_cli_test

data_dir = "{}/test_data".format(os.path.dirname(os.path.realpath(__file__)))
output_dir = "{}/output_data".format(os.path.dirname(os.path.realpath(__file__)))


def echo_task(task):
    return Result(host=task.host, result="Hello from Brigade")


def data_with_greeting(task):
    task.run(task=echo_task)
    task.run(task=load_yaml, file="{}/sample.yaml".format(data_dir))


def read_data(task):
    task.run(task=echo_task)
    r = task.run(task=load_yaml, file="{}/{}.yaml".format(data_dir, task.host))
    return Result(host=task.host, result=r.result["data"], changed=r.result["changed"])


class Test(object):

    @wrap_cli_test(output="{}/basic_single".format(output_dir))
    def test_print_basic(self, brigade):
        filter = brigade.filter(name="dev1.group_1")
        result = filter.run(echo_task)
        print_result(result)

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
        result = filter.run(read_data)
        print_result(result)
