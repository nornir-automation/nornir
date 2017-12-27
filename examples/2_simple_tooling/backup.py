#!/usr/bin/env python
"""
This is a simple example where we use click and brigade to build a simple CLI tool to retrieve
hosts information.

The main difference with get_facts_simple.py is that instead of calling a plugin directly
we wrap it in a function. It is not very useful or necessary here but illustrates how
tasks can be grouped.
"""
from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import files, networking, text

import click


def backup(task, path):
    result = task.run(networking.napalm_get,
                      getters="config")

    return task.run(files.write,
                    content=result.result["config"]["running"],
                    filename="{}/{}".format(path, task.host))


@click.command()
@click.option('--filter', '-f', multiple=True)
@click.option('--path', '-p', default=".")
def main(filter, path):
    """
    Backups running configuration of devices into a file
    """
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=False,
        config=Config(raise_on_error=False),
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices
    results = filtered.run(backup, num_workers=20, path=path)

    # Let's print the result on screen
    filtered.run(text.print_result,
                 num_workers=1,  # we are printing on screen so we want to do this synchronously
                 data=results)


if __name__ == "__main__":
    main()
