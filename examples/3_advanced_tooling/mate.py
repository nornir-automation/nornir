#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""

from brigade.core import Brigade
from brigade.core.configuration import Config
from brigade.plugins.inventory.simple import SimpleInventory

import click

from tasks import backup, configure, get_facts, validate


@click.group()
@click.option('--filter', '-f', multiple=True)
@click.option('--commit/--no-commit', '-c', default=False)
@click.pass_context
def run(ctx, filter, commit):
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=not commit,
        config=Config(raise_on_error=False),
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices
    ctx.obj["filtered"] = filtered


run.add_command(backup.backup)
run.add_command(configure.configure)
run.add_command(get_facts.get)
run.add_command(validate.validate)


if __name__ == "__main__":
    run(obj={})
