"""
This is a simple example where we use click and brigade to build a simple CLI tool to retrieve
hosts information.

The main difference with get_facts_simple.py is that instead of calling a plugin directly
we wrap it in a function. It is not very useful or necessary here but illustrates how
tasks can be grouped.
"""
import datetime

from brigade.core import Brigade
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import files, networking

import click

date = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(task, path):
    result = task.run(networking.napalm_get,
                      getters="config")

    task.run(files.write,
             content=result.result["get_config"]["running"],
             filename="path/{}/{}".format(task.host, date))


@click.command()
@click.option('--filter', '-f', multiple=True)
@click.option('--path', '-p', default=".")
def main(filter, path):
    """
    Backups running configuration of devices into a file
    """
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=True,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices
    filtered.run(backup, path=path, num_workers=1)


if __name__ == "__main__":
    main()
