#!/usr/bin/env python
"""
In this example we write a CLI tool with brigade and click to deploy configuration.
"""
from brigade.core import Brigade
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import data, networking, text

import click


def validate(task):
    task.host["config"] = ""

    r = task.run(name="read data",
                 task=data.load_yaml,
                 file="../extra_data/{host}/l3.yaml")

    validation_rules = [{
        'get_bgp_neighbors': {
            'global': {
                'peers': {
                    '_mode': 'strict',
                }
            }
        }
    }]
    peers = validation_rules[0]['get_bgp_neighbors']['global']['peers']
    for session in r.result['sessions']:
        peers[session['ipv4']] = {'is_up': True}

    return task.run(name="validating data",
                    task=networking.napalm_validate,
                    validation_source=validation_rules)


def print_compliance(task, results):
    task.run(name="print result",
             task=text.print_result,
             data=results[task.host.name],
             failed=not results[task.host.name].result['complies'],
             )


@click.command()
@click.option('--filter', '-f', multiple=True)
@click.option('--commit/--no-commit', '-c', default=False)
def main(filter, commit):
    brigade = Brigade(
        inventory=SimpleInventory("../hosts.yaml", "../groups.yaml"),
        dry_run=False,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    filtered = brigade.filter(**filter_dict)            # let's filter the devices

    results = filtered.run(task=validate)

    filtered.run(print_compliance,
                 results=results,
                 num_workers=1)


if __name__ == "__main__":
    main()
