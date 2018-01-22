#!/usr/bin/env python
"""
Runbook that downloads the configuration from the devices and
stores them on disk.
"""
from brigade.easy import easy_brigade
from brigade.plugins.tasks import files, networking, text


def backup(task):
    """
    This function groups two tasks:
        1. Download configuration from the device
        2. Store to disk
    """
    result = task.run(networking.napalm_get,
                      name="Gathering configuration",
                      getters="config")

    task.run(files.write,
             name="Saving Configuration to disk",
             content=result.result["config"]["running"],
             filename="./backups/{}".format(task.host))


brg = easy_brigade(
        host_file="../inventory/hosts.yaml",
        group_file="../inventory/groups.yaml",
        dry_run=False,
        raise_on_error=True,
)

# select which devices we want to work with
filtered = brg.filter(type="network_device", site="cmh")

# Run the ``backup`` function that groups the tasks to
# download/store devices' configuration
results = filtered.run(backup,
                       name="Backing up configurations")

# Let's print the result on screen
filtered.run(text.print_result,
             num_workers=1,  # task should be done synchronously
             data=results,
             task_id=-1,  # we only want to print the last task
             )
