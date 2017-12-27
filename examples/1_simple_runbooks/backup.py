#!/usr/bin/env python
from brigade.easy import easy_brigade
from brigade.plugins.tasks import files, networking, text


def backup(task):
    result = task.run(networking.napalm_get,
                      getters="config")

    return task.run(files.write,
                    content=result.result["config"]["running"],
                    filename="./backups/{}".format(task.host))


brigade = easy_brigade(
        hosts="../hosts.yaml", groups="../groups.yaml",
        dry_run=False,
        raise_on_error=False,
)

# select which devices we want to work with
filtered = brigade.filter(type="network_device", site="cmh")
results = filtered.run(backup)

# Let's print the result on screen
filtered.run(text.print_result,
             num_workers=1,  # we are printing on screen so we want to do this synchronously
             data=results)
