#!/usr/bin/env python
"""
This is a very simple scripts to get facts and print them on the screen.
"""
from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import networking, text

brigade = Brigade(
    inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
    dry_run=True,
    config=Config(raise_on_error=False),
)

# select which devices we want to work with
filtered = brigade.filter(type="network_device", site="cmh")

# we are going to gather "interfaces" and "facts" information with napalm
results = filtered.run(networking.napalm_get,
                       getters=["interfaces", "facts"])

# Let's print the result on screen
filtered.run(text.print_result,
             num_workers=1,  # we are printing on screen so we want to do this synchronously
             data=results)
