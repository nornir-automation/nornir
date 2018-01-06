#!/usr/bin/env python
"""
This is a very simple runbook to get facts and print them on the screen.
"""

from brigade.easy import easy_brigade
from brigade.plugins.functions.text import print_title
from brigade.plugins.tasks.networking import napalm_get
from brigade.plugins.tasks.text import print_result


brigade = easy_brigade(
        hosts="../hosts.yaml", groups="../groups.yaml",
        dry_run=True,
        raise_on_error=False,
)

print_title("Getting interfaces and facts")

# select which devices we want to work with
filtered = brigade.filter(type="network_device", site="cmh")

# we are going to gather "interfaces" and "facts" information with napalm
results = filtered.run(napalm_get,
                       getters=["interfaces", "facts"])

# Let's print the result on screen
filtered.run(print_result,
             num_workers=1,  # we are printing on screen so we want to do this synchronously
             data=results)
