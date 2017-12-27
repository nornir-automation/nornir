#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import data, networking, text

import click


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


@click.command()
@click.option('--filter', '-f', multiple=True)
@click.option('--commit/--no-commit', '-c', default=False)
def main(filter, commit):
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=not commit,
        config=Config(raise_on_error=False),
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices

    results = filtered.run(task=configure)

    filtered.run(text.print_result,
                 num_workers=1,  # we are printing on screen so we want to do this synchronously
                 data=results)


if __name__ == "__main__":
    main()
