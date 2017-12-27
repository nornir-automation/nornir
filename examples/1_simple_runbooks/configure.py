#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import data, networking, text


def configure(task):
    r = task.run(text.template_file,
                 template="base.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] = r.result

    r = task.run(data.load_yaml,
                 file="../extra_data/{host}/l3.yaml")
    task.host["l3"] = r.result

    r = task.run(text.template_file,
                 template="interfaces.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 template="routing.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    r = task.run(text.template_file,
                 template="{role}.j2",
                 path="../templates/{brigade_nos}")
    task.host["config"] += r.result

    return task.run(networking.napalm_configure,
                    replace=False,
                    configuration=task.host["config"])


brigade = Brigade(
    inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
    dry_run=False,
    config=Config(raise_on_error=False),
)

filtered = brigade.filter(type="network_device", site="cmh")

results = filtered.run(task=configure)

filtered.run(text.print_result,
             num_workers=1,  # we are printing on screen so we want to do this synchronously
             data=results)
