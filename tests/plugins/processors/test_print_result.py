import logging
import os

from nornir.core.task import Result
from nornir.plugins.processors.print_result import PrintResult

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

    elif "dev5.no_group" == task.host.name:
        data["values"] = [13, 14, 15]

    if data["failed"]:
        raise Exception("Unknown Error -> Contact your system administrator")

    return Result(host=task.host, changed=data["changed"], result=data["values"])


def read_data(task):
    task.run(task=echo_task, severity_level=logging.DEBUG)
    task.run(task=echo_task, msg="CRITICAL", severity_level=logging.CRITICAL)
    task.run(task=parse_data, severity_level=logging.WARN)


class Test(object):
    @wrap_cli_test(output="{}/basic_single".format(output_dir), save_output=False)
    def test_print_basic(self, nornir):
        nr = nornir.with_processors([PrintResult()]).filter(name="dev1.group_1")
        nr.run(echo_task)

    @wrap_cli_test(output="{}/basic_inventory".format(output_dir), save_output=False)
    def test_print_basic_inventory(self, nornir):
        nornir.with_processors([PrintResult()]).run(echo_task)

    @wrap_cli_test(output="{}/subtask_one_host".format(output_dir), save_output=False)
    def test_print_subtask_one_host(self, nornir):
        nornir.with_processors([PrintResult()]).run(data_with_greeting)

    @wrap_cli_test(output="{}/changed_host".format(output_dir), save_output=False)
    def test_print_changed_host(self, nornir):
        nr = nornir.with_processors([PrintResult()]).filter(site="site1")
        nr.run(read_data, severity_level=logging.WARN)

    @wrap_cli_test(
        output="{}/failed_with_severity".format(output_dir), save_output=False
    )
    def test_print_failed_with_severity(self, nornir):
        nornir.config.logging.configure()
        nr = nornir.with_processors([PrintResult(severity_level=logging.ERROR)])
        nr.run(read_data)
