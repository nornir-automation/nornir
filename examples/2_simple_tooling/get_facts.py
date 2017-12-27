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
from brigade.plugins.tasks import networking, text

import click


@click.command()
@click.option('--filter', '-f', multiple=True,
              help="k=v pairs to filter the devices")
@click.option('--get', '-g', multiple=True,
              help="getters you want to use")
def main(filter, get):
    """
    Retrieve information from network devices using napalm
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

    # Let's print the result on screen
    filtered.run(text.print_result,
                 num_workers=1,  # we are printing on screen so we want to do this synchronously
                 data=results)


if __name__ == "__main__":
    main()
