#!/usr/bin/env python
"""
Runbook to configure datacenter
"""
from brigade.easy import easy_brigade
from brigade.plugins.functions.text import print_title
from brigade.plugins.tasks import data, networking, text


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


brg = easy_brigade(
        host_file="../inventory/hosts.yaml",
        group_file="../inventory/groups.yaml",
        dry_run=False,
        raise_on_error=True,
)


# select which devices we want to work with
filtered = brg.filter(type="network_device", site="cmh")

results = filtered.run(task=configure)

print_title("Playbook to configure the network")
filtered.run(text.print_result,
             name="Configure device",
             num_workers=1,  # task should be done synchronously
             data=results,
             task_id=-1,  # we only want to print the last task
             )
