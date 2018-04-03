#!/usr/bin/env python
"""
Tool to rollback configuration from a saved configuration
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import networking, text

import click


def rollback(task, path):
    """
    This function loads the backup from ./$path/$hostname and
    deploys it.
    """
    task.run(
        networking.napalm_configure,
        name="Loading Configuration on the device",
        replace=True,
        filename="{}/{}".format(path, task.host),
    )


@click.command()
@click.option("--filter", "-f", multiple=True, help="k=v pairs to filter the devices")
@click.option(
    "--commit/--no-commit",
    "-c",
    default=False,
    help="whether you want to commit the changes or not",
)
@click.option("--path", "-p", default=".", help="Where to save the backup files")
def main(filter, commit, path):
    brg = easy_brigade(
        host_file="../inventory/hosts.yaml",
        group_file="../inventory/groups.yaml",
        dry_run=not commit,
        raise_on_error=True,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    # let's filter the devices
    filtered = brg.filter(**filter_dict)

    results = filtered.run(task=rollback, path=path)

    filtered.run(
        text.print_result,
        num_workers=1,  # task should be done synchronously
        data=results,
        task_id=-1,  # we only want to print the last task
    )


if __name__ == "__main__":
    main()
