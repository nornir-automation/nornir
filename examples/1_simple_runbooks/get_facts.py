#!/usr/bin/env python
"""
Very simple runbook to get facts and print them on the screen.
"""

from brigade.easy import easy_brigade
from brigade.plugins.functions.text import print_title
from brigade.plugins.tasks import networking, text


brg = easy_brigade(
        host_file="../inventory/hosts.yaml",
        group_file="../inventory/groups.yaml",
        dry_run=False,
        raise_on_error=False,
)

print_title("Getting interfaces and facts")

# select which devices we want to work with
filtered = brg.filter(type="network_device", site="cmh")

# we are going to gather "interfaces" and "facts"
# information with napalm
results = filtered.run(networking.napalm_get,
                       getters=["interfaces", "facts"])

# Let's print the result on screen
filtered.run(text.print_result,
             num_workers=1,  # task should be done synchronously
             data=results,
             )
