#!/usr/bin/env python
"""
Runbook to rollback configuration from a saved configuration
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import networking, text

import click


def rollback(task):
    """
    This function loads the backup from ./backups/$hostname and
    deploys it.
    """
    task.run(networking.napalm_configure,
             name="Loading Configuration on the device",
             replace=True,
             filename="backups/{host}")


@click.command()
@click.option('--filter', '-f', multiple=True,
              help="k=v pairs to filter the devices")
@click.option('--get', '-g', multiple=True,
              help="getters you want to use")
def main(filter, get):
    brg = easy_brigade(
            host_file="../inventory/hosts.yaml",
            group_file="../inventory/groups.yaml",
            dry_run=False,
            raise_on_error=True,
    )


    # select which devices we want to work with
    filtered = brg.filter(type="network_device", site="cmh")

    results = filtered.run(task=rollback)

    filtered.run(text.print_result,
                 num_workers=1,  # task should be done synchronously
                 data=results,
                 task_id=-1,  # we only want to print the last task
                 )
if __name__ == "__main__":
    main()
