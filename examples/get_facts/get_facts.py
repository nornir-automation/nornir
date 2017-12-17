"""
This is a simple example where we use click and brigade to build a simple CLI tool to retrieve
hosts information.

The main difference with get_facts_simple.py is that instead of calling a plugin directly
we wrap it in a function. It is not very useful or necessary here but illustrates how
tasks can be grouped.
"""
import pprint

from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import networking

import click


@click.command()
@click.option('--filter', '-f', multiple=True)
@click.option('--get', '-g', multiple=True)
def main(filter, get):
    """
    Retrieve $facts from devices in $site with $role
    """
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=True,
        config=Config(raise_on_error=False),
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices
    results = filtered.run(networking.napalm_get,
                           getters=get)

    for host, result in results.items():
        click.secho("* " + host, fg="blue")             # print host name in blue
        pprint.pprint(result.result)                    # print result nicely

    for host, error in results.tracebacks.items():
        click.secho("* " + host, fg="red")             # print host name in blue
        click.secho(error)                             # print host name in blue


if __name__ == "__main__":
    main()
