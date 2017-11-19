"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
import logging

from brigade.core import Brigade
from brigade.plugins import tasks
from brigade.plugins.inventory.simple import SimpleInventory

import click


def base_config(task):
    """
    1. logs all the facts, even the ones inherited from groups
    2. Creates a placeholder for device configuration
    3. Initializes some basic configuration
    """
    logging.info({task.host.name: task.host.expanded_data()})

    task.host["config"] = ""

    r = tasks.template_file(task=task,
                            template="base.j2",
                            path="templates/base/{nos}")
    task.host["config"] += r["result"]


def configure_interfaces(task):
    """
    1. Load interface data from an external yaml file
    2. Creates interface configuration
    """
    r = tasks.load_yaml(task=task,
                        file="extra_data/{host}/interfaces.yaml")
    task.host["interfaces"] = r["result"]

    r = tasks.template_file(task=task,
                            template="interfaces.j2",
                            path="templates/interfaces/{nos}")
    task.host["config"] += r["result"]


def deploy_config(task):
    """
    1. Load configuration into the device
    2. Prints diff
    """
    r = tasks.napalm_configure(task=task,
                               replace=False,
                               configuration=task.host["config"])

    click.secho("--- {} ({})".format(task.host, r["changed"]), fg="blue", bold=True)
    click.secho(r["diff"], fg='yellow')
    click.echo()


@click.command()
@click.option('--commit/--no-commit', default=False)
@click.option('--debug/--no-debug', default=False)
@click.argument('site')
@click.argument('role')
def deploy(commit, debug, site, role):
    logging.basicConfig(
        filename="log",
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    brigade = Brigade(
        inventory=SimpleInventory("hosts.yaml", "groups.yaml"),
        dry_run=not commit,
    )

    filtered = brigade.filter(site=site, role=role)
    filtered.run(task=base_config)
    filtered.run(task=configure_interfaces)
    filtered.run(task=deploy_config)


if __name__ == "__main__":
    deploy()
