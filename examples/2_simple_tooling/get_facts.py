#!/usr/bin/env python
"""
Very simple tool to get facts and print them on the screen.
"""
from brigade.easy import easy_brigade
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
    brg = easy_brigade(
            host_file="../inventory/hosts.yaml",
            group_file="../inventory/groups.yaml",
            dry_run=False,
            raise_on_error=False,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    # select which devices we want to work with
    filtered = brg.filter(**filter_dict)
    results = filtered.run(networking.napalm_get,
                           getters=get)

    # Let's print the result on screen
    filtered.run(text.print_result,
                 num_workers=1,  # task should be done synchronously
                 data=results)


if __name__ == "__main__":
    main()
