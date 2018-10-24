import logging
import os

from nornir.core.task import Result
from nornir.plugins.functions.text import print_result
from nornir.plugins.functions.text import print_title

from tests.wrapper import wrap_cli_test

output_dir = "{}/output_data".format(os.path.dirname(os.path.realpath(__file__)))


def echo_task(task, msg="Nornir"):
    return Result(
        host=task.host,
        result="Hello from {}".format(msg),
        output="Hello from {}".format(msg),
    )


def load_data(task):
    data = {"os": "Linux", "services": ["http", "smtp", "dns"]}
    return Result(host=task.host, result=data)


def data_with_greeting(task):
    task.run(task=echo_task)
    task.run(task=load_data)


def parse_data(task):

    data = {}
    data["failed"] = False
    data["changed"] = False

    if "dev1.group_1" == task.host.name:
        data["values"] = [1, 2, 3]
        data["changed"] = True

    elif "dev2.group_1" == task.host.name:
        data["values"] = [4, 5, 6]

    elif "dev3.group_2" == task.host.name:
        data["values"] = [7, 8, 9]

    elif "dev4.group_2" == task.host.name:
        data["values"] = [10, 11, 12]
        data["changed"] = False
        data["failed"] = True

    if data["failed"]:
        raise Exception("Unknown Error -> Contact your system administrator")

    return Result(host=task.host, changed=data["changed"], result=data["values"])


def read_data(task):
    task.run(task=echo_task, severity_level=logging.DEBUG)
    task.run(task=echo_task, msg="CRITICAL", severity_level=logging.CRITICAL)
    task.run(task=parse_data, severity_level=logging.WARN)


class Test(object):
    @wrap_cli_test(output="{}/basic_single".format(output_dir))
    def test_print_basic(self, nornir):
        filter = nornir.filter(name="dev1.group_1")
        result = filter.run(echo_task)
        print_result(result, vars="result")

    @wrap_cli_test(output="{}/basic_inventory".format(output_dir))
    def test_print_basic_inventory(self, nornir):
        result = nornir.run(echo_task)
        print_result(result)

    @wrap_cli_test(output="{}/basic_inventory_one_host".format(output_dir))
    def test_print_basic_inventory_one_host(self, nornir):
        result = nornir.run(data_with_greeting)
        print_result(result["dev2.group_1"])

    @wrap_cli_test(output="{}/basic_inventory_one_task".format(output_dir))
    def test_print_basic_inventory_one_task(self, nornir):
        result = nornir.run(data_with_greeting)
        print_result(result["dev2.group_1"][1])

    @wrap_cli_test(output="{}/multiple_tasks".format(output_dir))
    def test_print_multiple_tasks(self, nornir):
        result = nornir.run(data_with_greeting)
        print_title("Behold the data!")
        print_result(result)

    @wrap_cli_test(output="{}/changed_host".format(output_dir))
    def test_print_changed_host(self, nornir):
        filter = nornir.filter(site="site1")
        result = filter.run(read_data, severity_level=logging.WARN)
        print_result(result)

    @wrap_cli_test(output="{}/failed_with_severity".format(output_dir))
    def test_print_failed_with_severity(self, nornir):
        result = nornir.run(read_data)
        print_result(result, vars=["exception", "output"], severity_level=logging.ERROR)
