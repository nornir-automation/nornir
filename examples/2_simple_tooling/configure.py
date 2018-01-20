#!/usr/bin/env python
"""
Tool to configure datacenter
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import data, networking, text

import click


def configure(task):
    """
    This function groups all the tasks needed to configure the
    network:

        1. Loading extra data
        2. Templates to build configuration
        3. Deploy configuration on the device
    """
    r = task.run(text.template_file,
                 name="Base Configuration",
                 template="base.j2",
                 path="../templates/{brigade_nos}")
    # r.result holds the result of rendering the template
    # we store in the host itself so we can keep updating
    # it as we render other templates
    task.host["config"] = r.result

    r = task.run(data.load_yaml,
                 name="Loading extra data",
                 file="../extra_data/{host}/l3.yaml")
    # r.result holds the data contained in the yaml files
    # we load the data inside the host itself for further use
    task.host["l3"] = r.result

    r = task.run(text.template_file,
                 name="Interfaces Configuration",
                 template="interfaces.j2",
                 path="../templates/{brigade_nos}")
    # we update our hosts' config
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 name="Routing Configuration",
                 template="routing.j2",
                 path="../templates/{brigade_nos}")
    # we update our hosts' config
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 name="Role-specific Configuration",
                 template="{role}.j2",
                 path="../templates/{brigade_nos}")
    # we update our hosts' config
    task.host["config"] += r.result

    task.run(networking.napalm_configure,
             name="Loading Configuration on the device",
             replace=False,
             configuration=task.host["config"])


@click.command()
@click.option('--filter', '-f', multiple=True,
              help="k=v pairs to filter the devices")
@click.option('--commit/--no-commit', '-c', default=False,
              help="whether you want to commit the changes or not")
def main(filter, commit):
    brg = easy_brigade(
            host_file="../inventory/hosts.yaml",
            group_file="../inventory/groups.yaml",
            dry_run=not commit,
            raise_on_error=False,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    # let's filter the devices
    filtered = brg.filter(**filter_dict)

    results = filtered.run(task=configure)

    filtered.run(text.print_result,
                 num_workers=1,  # task should be done synchronously
                 data=results,
                 task_id=-1,  # we only want to print the last task
                 skipped=True,
                 )


if __name__ == "__main__":
    main()
