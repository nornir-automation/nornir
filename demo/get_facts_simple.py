"""
This is a simple example where we use click and brigade to build a simple CLI tool to retrieve
hosts information.
"""
from brigade.core import Brigade
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import networking

import click


@click.command()
@click.argument('site')
@click.argument('role')
@click.argument('facts')
def main(site, role, facts):
    brigade = Brigade(
        inventory=SimpleInventory("hosts.yaml", "groups.yaml"),
        dry_run=True,
    )

    filtered = brigade.filter(site=site, role=role)
    result = filtered.run(task=networking.napalm_get_facts,
                          facts=facts)

    for host, r in result.items():
        print(host)
        print("============")
        print(r["result"])
        print()


if __name__ == "__main__":
    main()
