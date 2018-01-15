#!/usr/bin/env python
"""
Tool that downloads the configuration from the devices and
stores them on disk.
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import files, networking, text

import click


def backup(task, path):
    """
    This function groups two tasks:
        1. Download configuration from the device
        2. Store to disk
    """
    result = task.run(networking.napalm_get,
                      name="Gathering configuration from the device",
                      getters="config")

    task.run(files.write,
             name="Saving Configuration to disk",
             content=result.result["config"]["running"],
             filename="{}/{}".format(path, task.host))


@click.command()
@click.option('--filter', '-f', multiple=True,
              help="filters to apply. For instance site=cmh")
@click.option('--path', '-p', default=".",
              help="Where to save the backup files")
def main(filter, path):
    """
    Backups running configuration of devices into a file
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

    # let's filter the devices
    filtered = brg.filter(**filter_dict)

    # Run the ``backup`` function that groups the tasks to
    # download/store devices' configuration
    results = filtered.run(backup,
                           name="Backing up configurations",
                           path=path)

    # Let's print the result on screen
    filtered.run(text.print_result,
                 num_workers=1,  # task should be done synchronously
                 data=results,
                 task_id=-1,  # we only want to print the last task
                 skipped=True,
                 )


if __name__ == "__main__":
    main()
