#!/usr/bin/env python
"""
Runbook that verifies that BGP sessions are configured and up.
"""
from brigade.easy import easy_brigade
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

    task.run(name="validating data",
             task=networking.napalm_validate,
             validation_source=validation_rules)


def print_compliance(task, results):
    """
    We use this task so we can access directly the result
    for each specific host and see if the task complies or not
    and pass it to print_result.
    """
    task.run(name="print result",
             task=text.print_result,
             data=results[task.host.name],
             failed=not results[task.host.name][2].result['complies'],
             )


@click.command()
@click.option('--filter', '-f', multiple=True,
              help="k=v pairs to filter the devices")
def main(filter):
    brg = easy_brigade(
            host_file="../inventory/hosts.yaml",
            group_file="../inventory/groups.yaml",
            dry_run=False,
            raise_on_error=True,
    )

    # filter is going to be a list of key=value so we clean that first
    filter_dict = {"type": "network_device"}
    for f in filter:
        k, v = f.split("=")
        filter_dict[k] = v

    # select which devices we want to work with
    filtered = brg.filter(**filter_dict)

    results = filtered.run(task=validate)

    filtered.run(print_compliance,
                 results=results,
                 num_workers=1)


if __name__ == "__main__":
    main()
